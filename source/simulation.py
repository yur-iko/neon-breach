"""Deterministic gameplay, collision and navigation, independent of rendering."""
from collections import deque
from dataclasses import dataclass, field
import json
import math
import random
from pathlib import Path
from content import WEAPONS, UPGRADES, ENEMIES, ARENAS, STAGE_COUNTS, SPAWNS


def clamp(value, low, high):
    return max(low, min(high, value))


def distance(a, b):
    return math.sqrt(sum((x-y)**2 for x,y in zip(a,b)))


def direction(yaw, pitch=0):
    y, p = math.radians(yaw), math.radians(pitch)
    return (-math.sin(y)*math.cos(p), math.cos(y)*math.cos(p), math.sin(p))


def ray_box(origin, vector, low, high, limit=100):
    near, far = 0., limit
    for o,d,a,b in zip(origin, vector, low, high):
        if abs(d)<1e-9:
            if o<a or o>b:
                return None
        else:
            p,q = (a-o)/d, (b-o)/d
            near,far = max(near,min(p,q)), min(far,max(p,q))
            if near>far:
                return None
    return near


class Arena:
    def __init__(self, index):
        self.index = index
        self.boxes = ARENAS[index]["boxes"]
        self.solids = list(self.boxes) + [(0,-22.5,23,.5,8),(0,22.5,23,.5,8),(-22.5,0,.5,23,8),(22.5,0,.5,23,8)]
        self.cells = {(x,y) for x in range(29) for y in range(29) if self.free(*self.point((x,y)), 1.3)}
        self.flow = {}

    @staticmethod
    def point(cell):
        return (cell[0]*1.5-21, cell[1]*1.5-21)

    def cell(self, x, y):
        c = (round((x+21)/1.5), round((y+21)/1.5))
        return c if c in self.cells else min(self.cells,key=lambda q:distance(self.point(q),(x,y)))

    def free(self, x, y, radius=.35):
        if not (-22+radius<x<22-radius and -22+radius<y<22-radius):
            return False
        for bx,by,w,d,h in self.boxes:
            cx,cy = clamp(x,bx-w,bx+w),clamp(y,by-d,by+d)
            if (x-cx)**2+(y-cy)**2<radius**2:
                return False
        return True

    def move(self, x, y, dx, dy, radius=.35):
        steps=max(1,math.ceil(math.hypot(dx,dy)/.18))
        for _ in range(steps):
            if self.free(x+dx/steps,y,radius): x+=dx/steps
            if self.free(x,y+dy/steps,radius): y+=dy/steps
        return x,y

    def wall_distance(self, origin, vector, limit=100):
        best=limit
        for x,y,w,d,h in self.solids:
            hit=ray_box(origin,vector,(x-w,y-d,0),(x+w,y+d,h),best)
            if hit is not None: best=min(best,hit)
        if vector[2]<0:
            best=min(best,max(0,-origin[2]/vector[2]))
        return best

    def visible(self, a, b):
        length=distance(a,b)
        if length<.01: return True
        vector=tuple((b[i]-a[i])/length for i in range(3))
        return self.wall_distance(a,vector,length)>=length-.02

    def update_flow(self,x,y):
        target=self.cell(x,y)
        self.flow={target:0}
        queue=deque([target])
        while queue:
            a,b=queue.popleft()
            for c in [(a-1,b),(a+1,b),(a,b-1),(a,b+1)]:
                if c in self.cells and c not in self.flow:
                    self.flow[c]=self.flow[(a,b)]+1
                    queue.append(c)

    def waypoint(self,x,y,goal):
        if self.visible((x,y,1),(goal[0],goal[1],1)):
            # Visibility is a thin ray; movement still uses radius-aware collision.
            if all(self.free(x+(goal[0]-x)*t/10,y+(goal[1]-y)*t/10,1.3) for t in range(1,11)):
                return goal
        a,b=self.cell(x,y)
        choices=[c for c in [(a,b),(a-1,b),(a+1,b),(a,b-1),(a,b+1)] if c in self.flow]
        return self.point(min(choices,key=lambda c:self.flow[c])) if choices else goal


@dataclass
class Enemy:
    uid:int
    kind:str
    x:float
    y:float
    hp:float
    max_hp:float
    radius:float
    height:float
    attack:float=1.5
    flash:float=0
    age:float=0
    phase:int=0
    telegraph:float=0
    stuck:float=0
    @property
    def center(self): return (self.x,self.y,self.height*.55)


@dataclass
class Projectile:
    uid:int
    pos:tuple
    velocity:tuple
    damage:float
    friendly:bool
    solar:bool=False
    life:float=6


@dataclass
class Field:
    uid:int
    x:float
    y:float
    radius:float
    life:float


class Game:
    def __init__(self, seed=42):
        self.rng=random.Random(seed)
        self.upgrades={u[0]:0 for u in UPGRADES}
        self.stage=1
        self.credits=0
        self.kills=0
        self.total_time=0
        self.state="menu"
        self.events=[]
        self.uid=0
        self.weapon=0
        self.yaw=0
        self.pitch=0
        self.aim=False
        self.start_stage(1)
        self.state="menu"

    @property
    def max_health(self): return 100+self.upgrades["health"]*25

    @property
    def unlocked(self): return [i for i,w in enumerate(WEAPONS) if w["unlock"]<=self.stage]

    def magazine(self, i): return round(WEAPONS[i]["magazine"]*(1+.2*self.upgrades["magazine"]))

    def new_id(self):
        self.uid+=1
        return self.uid

    def emit(self, kind, **kwargs): self.events.append(dict(kind=kind,**kwargs))

    def start_stage(self, stage):
        self.stage=stage
        self.arena=Arena((stage-1)%3)
        self.x,self.y=0.,-18.
        self.yaw,self.pitch=0.,0.
        self.hp=float(self.max_health)
        self.enemies=[]
        self.projectiles=[]
        self.fields=[]
        self.cooldowns=[0.]*5
        self.ammo=[self.magazine(i) for i in range(5)]
        self.reload_left=0.
        self.shot_timer=0.
        self.overdrive=0.
        self.pending=STAGE_COUNTS[stage-1]
        self.spawn_timer=.6
        self.flow_timer=0.
        self.stage_time=0.
        self.boss_spawned=False
        self.weapon=min(self.weapon,max(self.unlocked))
        self.state="playing"
        self.events=[]
        self.arena.update_flow(self.x,self.y)
        self.emit("stage",stage=stage)

    def spawn(self,kind=None,pos=None):
        if kind is None:
            choices=["hunter"]*4
            if self.stage>=2: choices += ["ranger"]*3
            if self.stage>=3: choices += ["flanker"]*3
            if self.stage>=4: choices += ["heavy"]*2
            kind=self.rng.choice(choices)
        if pos is None:
            candidates=[p for p in SPAWNS if distance(p,(self.x,self.y))>11 and all(distance(p,(e.x,e.y))>2 for e in self.enemies)]
            if not candidates: return None
            pos=self.rng.choice(candidates)
        spec=ENEMIES[kind]
        hp=spec["hp"]*(1+.075*(self.stage-1)) if kind!="boss" else spec["hp"]
        enemy=Enemy(self.new_id(),kind,*pos,hp,hp,spec["radius"],spec["height"],attack=1.8+self.rng.random())
        self.enemies.append(enemy)
        self.emit("spawn",pos=enemy.center,color=spec["color"])
        return enemy

    def switch(self,index):
        if self.state=="playing" and index in self.unlocked:
            self.weapon=index
            self.reload_left=0
            self.shot_timer=max(.15,self.shot_timer)

    def reload(self):
        if self.state=="playing" and not self.reload_left and self.ammo[self.weapon]<self.magazine(self.weapon):
            self.reload_left=WEAPONS[self.weapon]["reload"]*(1-.12*self.upgrades["reload"])
            self.emit("reload")

    def hit(self,enemy,damage,push=0):
        if enemy not in self.enemies: return
        enemy.hp-=damage
        enemy.flash=.13
        if push:
            dx,dy=enemy.x-self.x,enemy.y-self.y
            length=max(.1,math.hypot(dx,dy))
            enemy.x,enemy.y=self.arena.move(enemy.x,enemy.y,dx/length*push,dy/length*push,enemy.radius)
        self.emit("hit",pos=enemy.center)
        if enemy.hp<=0:
            self.enemies.remove(enemy)
            reward=ENEMIES[enemy.kind]["reward"]
            self.credits+=reward
            self.kills+=1
            self.hp=min(self.max_health,self.hp+2*self.upgrades["heal"])
            self.emit("kill",pos=enemy.center,color=ENEMIES[enemy.kind]["color"],reward=reward)

    def damage_player(self, damage):
        if self.state!="playing": return
        self.hp=max(0,self.hp-damage*(1-.08*self.upgrades["armor"]))
        self.emit("hurt")
        if self.hp<=0:
            self.state="dead"
            self.emit("death")

    def hitscan(self, vector, damage, pierce=False, push=0, color=(.2,.9,1)):
        origin=(self.x,self.y,1.65)
        wall=self.arena.wall_distance(origin,vector,75)
        targets=[]
        for e in self.enemies:
            t=ray_box(origin,vector,(e.x-e.radius,e.y-e.radius,.1),(e.x+e.radius,e.y+e.radius,e.height),wall)
            if t is not None: targets.append((t,e))
        targets.sort(key=lambda v:v[0])
        if not pierce: targets=targets[:1]
        end=wall if pierce or not targets else targets[0][0]
        for _,e in targets: self.hit(e,damage,push)
        endpoint=tuple(origin[i]+vector[i]*end for i in range(3))
        self.emit("beam",start=origin,end=endpoint,color=color)
        return [e for _,e in targets]

    def shoot(self, special=False):
        if self.state!="playing" or self.reload_left or self.shot_timer>0: return False
        w=WEAPONS[self.weapon]
        if special and self.cooldowns[self.weapon]>0: return False
        if not special and self.ammo[self.weapon]<=0 and not(self.weapon==2 and self.overdrive>0):
            self.reload()
            return False
        if special:
            self.cooldowns[self.weapon]=w["cooldown"]*(1-.12*self.upgrades["cooldown"])
        elif not(self.weapon==2 and self.overdrive>0):
            self.ammo[self.weapon]-=1
        self.shot_timer=w["interval"]*(.48 if self.weapon==2 and self.overdrive>0 else 1)
        base=w["damage"]*(1+.12*self.upgrades["damage"])
        if self.weapon==3: base*=1+.15*self.upgrades["rail"]
        aim=direction(self.yaw,self.pitch)
        self.emit("shoot",weapon=self.weapon,special=special)
        if self.weapon==2 and special:
            self.overdrive=4+1.5*self.upgrades["rifle"]
            self.shot_timer=.05
        elif self.weapon==1 and special:
            for e in list(self.enemies):
                dx,dy=e.x-self.x,e.y-self.y
                dist=max(.1,math.hypot(dx,dy))
                if dist<10 and (dx*aim[0]+dy*aim[1])/dist>.35 and self.arena.visible((self.x,self.y,1.3),e.center):
                    self.hit(e,65*(1+.12*self.upgrades["damage"]),4+self.upgrades["shotgun"])
            self.emit("burst",pos=(self.x+aim[0]*3,self.y+aim[1]*3,1),color=w["color"])
        elif self.weapon==4:
            self.projectiles.append(Projectile(self.new_id(),(self.x,self.y,1.65),tuple(v*23 for v in aim),base,True,special))
        else:
            count=w["pellets"]+(2*self.upgrades["shotgun"] if self.weapon==1 else 0)
            spread=w["spread"]*(1-.2*self.upgrades["aim"])*(.35 if self.aim else 1)
            if special: count,spread=1,0
            struck=[]
            for _ in range(count):
                vec=tuple(aim[i]+self.rng.uniform(-spread,spread) for i in range(3))
                length=math.sqrt(sum(v*v for v in vec))
                vec=tuple(v/length for v in vec)
                struck+=self.hitscan(vec,base*(3 if special else 1),self.weapon==3 or (self.weapon==0 and (special or self.upgrades["pistol"])),.12*(1+self.upgrades["shotgun"]) if self.weapon==1 else 0,w["color"])
            if self.weapon==3 and special and struck:
                anchor=struck[0]
                nearby=sorted([e for e in self.enemies if e not in struck],key=lambda e:distance(e.center,anchor.center))
                linked=0
                for e in nearby:
                    if distance(anchor.center,e.center)<9 and self.arena.visible(anchor.center,e.center):
                        self.emit("beam",start=anchor.center,end=e.center,color=w["color"])
                        self.hit(e,base*.85)
                        linked+=1
                        if linked>=2+self.upgrades["rail"]: break
        return True

    def explode(self, projectile):
        pos=projectile.pos
        radius=4*(1+.2*self.upgrades["blast"])
        self.emit("explosion",pos=pos,radius=radius)
        # Lift wall-impact origin slightly back toward the incoming direction.
        for e in list(self.enemies):
            d=distance(pos,e.center)
            if d<radius and self.arena.visible(pos,e.center): self.hit(e,projectile.damage*(1-.65*d/radius),.5)
        if projectile.solar:
            self.fields.append(Field(self.new_id(),pos[0],pos[1],radius,5+1.5*self.upgrades["field"]))

    def enemy_fire(self,e,spread=0,speed=11):
        origin=(e.x,e.y,min(e.height*.7,2.2))
        target=(self.x,self.y,1.35)
        d=distance(origin,target)
        vector=tuple((target[i]-origin[i])/max(d,.01) for i in range(3))
        angle=math.atan2(vector[1],vector[0])+spread
        horizontal=math.hypot(vector[0],vector[1])
        vel=(math.cos(angle)*horizontal*speed,math.sin(angle)*horizontal*speed,vector[2]*speed)
        self.projectiles.append(Projectile(self.new_id(),origin,vel,ENEMIES[e.kind]["damage"]*(1+.035*self.stage),False))

    def step(self, dt, forward=0, strafe=0, sprint=False, fire=False):
        if self.state!="playing": return
        dt=clamp(dt,0,.05)
        self.stage_time+=dt
        self.total_time+=dt
        self.shot_timer=max(0,self.shot_timer-dt)
        self.overdrive=max(0,self.overdrive-dt)
        self.cooldowns=[max(0,c-dt) for c in self.cooldowns]
        if self.reload_left:
            self.reload_left=max(0,self.reload_left-dt)
            if not self.reload_left: self.ammo[self.weapon]=self.magazine(self.weapon)
        speed=6.2*(1+.08*self.upgrades["speed"])*(1.5 if sprint else 1)*(.62 if self.aim else 1)
        length=max(1,math.hypot(forward,strafe))
        y=math.radians(self.yaw)
        dx=(-math.sin(y)*forward+math.cos(y)*strafe)/length*speed*dt
        dy=(math.cos(y)*forward+math.sin(y)*strafe)/length*speed*dt
        self.x,self.y=self.arena.move(self.x,self.y,dx,dy)
        if fire: self.shoot()
        self.flow_timer-=dt
        if self.flow_timer<=0:
            self.arena.update_flow(self.x,self.y)
            self.flow_timer=.65
        self.spawn_timer-=dt
        if self.pending and self.spawn_timer<=0 and len(self.enemies)<min(12,4+self.stage):
            if self.spawn():
                self.pending-=1
                self.spawn_timer=max(1.2,3-self.stage*.13)
        if self.stage==10 and not self.boss_spawned and self.pending<=8:
            if self.spawn("boss",(0,17)):
                self.boss_spawned=True
                self.emit("boss")
        for f in list(self.fields):
            f.life-=dt
            for e in list(self.enemies):
                if distance((e.x,e.y),(f.x,f.y))<f.radius and self.arena.visible((f.x,f.y,.2),e.center):
                    self.hit(e,25*(1+.12*self.upgrades["damage"])*dt)
            if f.life<=0: self.fields.remove(f)
        for e in list(self.enemies):
            e.age+=dt
            e.flash=max(0,e.flash-dt)
            e.attack-=dt
            dist=distance((e.x,e.y),(self.x,self.y))
            visible=self.arena.visible((e.x,e.y,min(e.height*.7,2.2)),(self.x,self.y,1.35))
            spec=ENEMIES[e.kind]
            if e.telegraph>0:
                e.telegraph-=dt
                if e.telegraph<=0:
                    if e.kind=="boss":
                        if e.phase%2:
                            for angle in [-.24,-.12,0,.12,.24]: self.enemy_fire(e,angle,12)
                        else:
                            for i in range(18):
                                a=i*math.tau/18
                                self.projectiles.append(Projectile(self.new_id(),(e.x,e.y,1.3),(math.cos(a)*9,math.sin(a)*9,0),18,False))
                        e.phase+=1
                        e.attack=2.4 if e.hp>e.max_hp*.5 else 1.7
                    else:
                        self.enemy_fire(e,0,8 if e.kind=="heavy" else 10)
                        e.attack=2.8 if e.kind=="heavy" else 2.1
            elif visible and e.attack<=0:
                if e.kind in ("hunter","flanker") and dist<1.25+e.radius:
                    self.damage_player(spec["damage"])
                    e.attack=.95
                elif e.kind in ("ranger","heavy","boss"):
                    e.telegraph=.8 if e.kind=="boss" else .6
            desired=(self.x,self.y)
            move=True
            if visible and e.kind in ("ranger","heavy","boss") and dist< (12 if e.kind!="boss" else 15): move=False
            if dist<.9+e.radius: move=False
            if move:
                tx,ty=self.arena.waypoint(e.x,e.y,desired)
                dx,dy=tx-e.x,ty-e.y
                d=max(.01,math.hypot(dx,dy))
                vx,vy=dx/d,dy/d
                if e.kind=="flanker" and visible and dist>3:
                    side=1 if e.uid%2 else -1
                    vx,vy=vx+vy*.5*side,vy-vx*.5*side
                speed=spec["speed"]*(1+.015*self.stage)
                if any(distance((e.x,e.y),(f.x,f.y))<f.radius and self.arena.visible((f.x,f.y,.2),e.center) for f in self.fields): speed*=.4
                # Separate actors so their silhouettes and shots remain readable.
                for other in self.enemies:
                    if other is e: continue
                    ox,oy=e.x-other.x,e.y-other.y
                    sep=math.hypot(ox,oy)
                    if .01<sep<e.radius+other.radius+.25:
                        vx+=ox/sep*.85; vy+=oy/sep*.85
                old=(e.x,e.y)
                e.x,e.y=self.arena.move(e.x,e.y,vx*speed*dt,vy*speed*dt,e.radius)
                e.stuck=e.stuck+dt if distance(old,(e.x,e.y))<.005 else 0
                if e.stuck>1.5:
                    # Recover locally to a clear neighbouring navigation point.
                    cell=self.arena.cell(e.x,e.y)
                    tx,ty=self.arena.point(cell)
                    e.x,e.y=self.arena.move(e.x,e.y,(tx-e.x)*dt*3,(ty-e.y)*dt*3,e.radius)
        for p in list(self.projectiles):
            p.life-=dt
            start=p.pos
            speed=math.sqrt(sum(v*v for v in p.velocity))
            vector=tuple(v/speed for v in p.velocity)
            travel=speed*dt
            wall=self.arena.wall_distance(start,vector,travel)
            hit=wall<travel-.0001
            nearest=wall
            if p.friendly:
                for e in self.enemies:
                    t=ray_box(start,vector,(e.x-e.radius,e.y-e.radius,0),(e.x+e.radius,e.y+e.radius,e.height),nearest)
                    if t is not None: nearest=t; hit=True
            else:
                t=ray_box(start,vector,(self.x-.38,self.y-.38,.2),(self.x+.38,self.y+.38,1.85),nearest)
                if t is not None:
                    nearest=t;hit=True;self.damage_player(p.damage)
            p.pos=tuple(start[i]+vector[i]*max(0,nearest-.03 if hit else nearest) for i in range(3))
            if hit or p.life<=0:
                if p.friendly: self.explode(p)
                self.projectiles.remove(p)
        if self.state=="playing" and self.pending==0 and not self.enemies and (self.stage!=10 or self.boss_spawned):
            self.credits+=85+self.stage*15
            self.state="victory" if self.stage==10 else "shop"
            self.emit(self.state)

    def cost(self,index):
        key,_,cost,_,_=UPGRADES[index]
        return round(cost*(1+self.upgrades[key]*.6))

    def buy(self,index):
        if self.state!="shop": return False
        key,_,_,cap,_=UPGRADES[index]
        cost=self.cost(index)
        if self.upgrades[key]>=cap or self.credits<cost: return False
        self.credits-=cost
        self.upgrades[key]+=1
        self.emit("purchase")
        return True

    def snapshot(self):
        return dict(version=1,stage=self.stage,credits=self.credits,kills=self.kills,total_time=self.total_time,upgrades=self.upgrades.copy(),state="shop" if self.state=="shop" else "checkpoint",weapon=self.weapon)

    def restore(self,data):
        if not isinstance(data,dict) or data.get("version")!=1: raise ValueError("Unsupported save")
        def integer(key,lo,hi):
            value=data.get(key)
            if type(value) is not int or not lo<=value<=hi: raise ValueError("Invalid "+key)
            return value
        stage=integer("stage",1,10)
        credits=integer("credits",0,1000000)
        kills=integer("kills",0,1000000)
        upgrades=data.get("upgrades")
        if not isinstance(upgrades,dict): raise ValueError("Invalid upgrades")
        clean={}
        for key,_,_,cap,_ in UPGRADES:
            value=upgrades.get(key,0)
            if type(value) is not int or not 0<=value<=cap: raise ValueError("Invalid upgrade")
            clean[key]=value
        duration=data.get("total_time",0)
        if not isinstance(duration,(float,int)) or not math.isfinite(duration) or not 0<=duration<=1e8: raise ValueError("Invalid play time")
        weapon=integer("weapon",0,4)
        state=data.get("state")
        if state not in ("shop","checkpoint"): raise ValueError("Invalid state")
        self.upgrades=clean
        self.credits,self.kills,self.total_time=credits,kills,duration
        self.weapon=weapon
        self.start_stage(stage)
        if state=="shop": self.state="shop"


class Storage:
    def __init__(self,folder):
        self.folder=Path(folder)
        self.folder.mkdir(parents=True,exist_ok=True)
        self.error=""

    def read(self,name):
        path=self.folder/(name+".json")
        try:
            if path.stat().st_size>100000: raise ValueError("Save too large")
            return json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError: return None
        except (OSError,ValueError,TypeError):
            self.error="Saved data could not be read. You can start a new run."
            return None

    def write(self,name,data):
        path=self.folder/(name+".json")
        temp=path.with_suffix(".tmp")
        try:
            temp.write_text(json.dumps(data,indent=2),encoding="utf-8")
            temp.replace(path)
            return True
        except OSError:
            self.error="Could not save. Check that the save folder is writable."
            return False
