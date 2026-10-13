"""Procedural low-poly geometry. No external models, textures or shaders."""
import math
import random
from panda3d.core import (Geom, GeomNode, GeomTriangles, GeomVertexData,
                         GeomVertexFormat, GeomVertexArrayFormat, GeomVertexWriter, NodePath, LineSegs,
                         TransparencyAttrib)
from content import ARENAS, ENEMIES, WEAPONS

array_format=GeomVertexArrayFormat()
array_format.addColumn("vertex",3,Geom.NTFloat32,Geom.CPoint)
array_format.addColumn("color",4,Geom.NTFloat32,Geom.CColor)
vertex_format=GeomVertexFormat()
vertex_format.addArray(array_format)
vertex_format=GeomVertexFormat.registerFormat(vertex_format)


def mesh(name, vertices, faces, color):
    data=GeomVertexData(name,vertex_format,Geom.UHStatic)
    vertex=GeomVertexWriter(data,"vertex")
    colors=GeomVertexWriter(data,"color")
    prim=GeomTriangles(Geom.UHStatic)
    i=0
    shades=[.64,.8,1,.72,.92,.55,.85,.68]
    for j,face in enumerate(faces):
        for k in range(1,len(face)-1):
            for idx in (face[0],face[k],face[k+1]):
                vertex.addData3(*vertices[idx])
                colors.addData4(*(v*shades[j%len(shades)] for v in color[:3]),color[3] if len(color)>3 else 1)
                prim.addVertex(i)
                i+=1
    geom=Geom(data)
    geom.addPrimitive(prim)
    node=GeomNode(name)
    node.addGeom(geom)
    return NodePath(node)


CUBE=[(-.5,-.5,-.5),(.5,-.5,-.5),(.5,.5,-.5),(-.5,.5,-.5),(-.5,-.5,.5),(.5,-.5,.5),(.5,.5,.5),(-.5,.5,.5)]
FACES=[(0,3,2,1),(0,1,5,4),(4,5,6,7),(1,2,6,5),(2,3,7,6),(3,0,4,7)]


def box(parent,pos,scale,color,name="box"):
    node=mesh(name,CUBE,FACES,color)
    node.reparentTo(parent)
    node.setPos(*pos)
    node.setScale(*scale)
    return node


def crystal(parent,pos,scale,color):
    vertices=[(1,0,0),(0,1,0),(-1,0,0),(0,-1,0),(0,0,1),(0,0,-1)]
    faces=[(0,1,4),(1,2,4),(2,3,4),(3,0,4),(1,0,5),(2,1,5),(3,2,5),(0,3,5)]
    node=mesh("crystal",vertices,faces,color)
    node.reparentTo(parent); node.setPos(*pos); node.setScale(*scale)
    return node


def line(parent,points,color,width=2):
    seg=LineSegs()
    seg.setThickness(width)
    seg.setColor(*color[:3],color[3] if len(color)>3 else 1)
    seg.moveTo(*points[0])
    for p in points[1:]: seg.drawTo(*p)
    node=parent.attachNewNode(seg.create())
    node.setLightOff()
    return node


def ring(parent,pos,radius,color,width=2):
    pts=[(math.cos(i*math.tau/32)*radius,math.sin(i*math.tau/32)*radius,0) for i in range(33)]
    node=line(parent,pts,color,width)
    node.setPos(*pos)
    return node


class Scene:
    def __init__(self,render):
        self.render=render
        self.world=None
        self.actors=render.attachNewNode("actors")
        self.enemy_nodes={}
        self.projectile_nodes={}
        self.field_nodes={}
        self.effects=[]

    def build(self,index):
        if self.world: self.world.removeNode()
        self.actors.removeNode()
        self.actors=self.render.attachNewNode("actors")
        self.enemy_nodes={};self.projectile_nodes={};self.field_nodes={};self.effects=[]
        self.world=self.render.attachNewNode("arena")
        spec=ARENAS[index];accent=spec["color"]
        box(self.world,(0,0,-.25),(46,46,.5),(.115,.155,.21))
        for x in range(-22,23,4):
            line(self.world,[(x,-22,.01),(x,22,.01)],(.18,.24,.3),1)
            line(self.world,[(-22,x,.01),(22,x,.01)],(.18,.24,.3),1)
        # Ground lanes and inset pads make the scale and routes legible.
        for x in (-20,20):
            box(self.world,(x,0,.015),(.07,40,.025),accent)
        for y in (-20,20):
            box(self.world,(0,y,.015),(40,.07,.025),accent)
        for x,y in [(-18,-17),(18,-17),(-18,17),(18,17),(0,19)]:
            ring(self.world,(x,y,.04),1.35,accent,3)
            box(self.world,(x,y,-.02),(2,2,.08),(.2,.25,.31))
        for x,y,w,d,h in spec["boxes"]:
            box(self.world,(x,y,h*.5),(w*2,d*2,h),(.2,.27,.34))
            box(self.world,(x,y,h+.1),(w*2+.15,d*2+.15,.2),(.32,.4,.47))
            for side in (-1,1):
                box(self.world,(x,y+side*(d+.015),h*.75),(w*1.6,.045,.08),accent)
                box(self.world,(x+side*(w+.02),y,h*.35),(.05,d*1.6,.12),(.47,.52,.52))
            box(self.world,(x-w+.25,y-d-.025,.45),(.25,.05,.55),(1,.64,.16))
        for x,y,sx,sy in [(0,-23,48,2),(0,23,48,2),(-23,0,2,48),(23,0,2,48)]:
            box(self.world,(x,y,3),(sx,sy,6),(.11,.16,.23))
            box(self.world,(x,y,5.5),(sx+.04,sy+.04,.16),accent)
        for x in range(-20,21,5):
            for y in (-21.8,21.8):
                box(self.world,(x,y,2.8),(.16,.15,4.8),(.23,.3,.38))
                box(self.world,(x,y-.1 if y>0 else y+.1,3.9),(.1,.06,1.4),accent)
        rng=random.Random(400+index)
        for i in range(40):
            a=i*math.tau/40
            x,y=math.cos(a)*rng.uniform(30,44),math.sin(a)*rng.uniform(30,44)
            h=rng.uniform(7,23)
            box(self.world,(x,y,h/2),(rng.uniform(2,5),rng.uniform(2,5),h),(.075,.105,.16))
            box(self.world,(x,y,h),(.2,.2,1),accent)
        self.world.flattenStrong()

    def enemy(self,e):
        root=self.actors.attachNewNode("enemy-"+str(e.uid))
        c=ENEMIES[e.kind]["color"]
        r,h=e.radius,e.height
        body=root.attachNewNode("body")
        shadow=ring(root,(0,0,.025),r*1.1,(*c,.35),2)
        if e.kind=="flanker":
            crystal(body,(0,0,h*.65),(r,r*1.15,h*.4),c)
            for s in (-1,1):
                limb=box(body,(s*r,.05,h*.35),(.14,.65,.15),(.27,.18,.35));limb.setR(s*35)
                crystal(body,(s*r,.32,h*.55),(.13,.4,.13),c)
        else:
            box(body,(0,0,h*.5),(r*1.65,r*1.1,h*.42),c)
            box(body,(0,0,h*.84),(r*1.1,r*.95,h*.24),(.26,.32,.4))
            box(body,(0,-r*.5,h*.85),(r*.85,.09,.13),(1,.92,.67))
            for s in (-1,1):
                box(body,(s*r*.48,0,h*.16),(r*.48,r*.8,h*.32),(.15,.2,.26))
                box(body,(s*r,.03,h*.52),(r*.42,r*.65,h*.37),c)
            crystal(body,(0,-r*.58,h*.55),(r*.3,.1,h*.1),(1,.85,.47))
            if e.kind in ("ranger","heavy"):
                box(body,(r,-r*.65,h*.6),(r*.5,r*1.5,r*.45),(.12,.17,.23))
                box(body,(r,-r*1.3,h*.6),(r*.4,.15,r*.32),c)
            if e.kind=="boss":
                for s in (-1,1):
                    crystal(body,(s*r*.8,0,h*.96),(.35,.35,.7),c)
                    box(body,(s*r*1.15,0,h*.67),(.6,.8,.8),(.29,.18,.3))
            elif e.kind=="hunter":
                for s in (-1,1):
                    crystal(body,(s*r,-.4,h*.3),(.1,.15,.45),(.8,.87,.93))
        body.flattenStrong()
        health=box(root,(0,0,h+.32),(r*1.8,.05,.075),(.24,1,.65))
        self.enemy_nodes[e.uid]=(root,body,health,shadow)
        return self.enemy_nodes[e.uid]

    def sync(self,game,dt):
        alive={e.uid for e in game.enemies}
        for uid in list(self.enemy_nodes):
            if uid not in alive:
                self.enemy_nodes.pop(uid)[0].removeNode()
        for e in game.enemies:
            root,body,bar,shadow=self.enemy_nodes.get(e.uid) or self.enemy(e)
            root.setPos(e.x,e.y,0)
            root.setH(math.degrees(math.atan2(game.x-e.x,-(game.y-e.y))))
            body.setZ(math.sin(e.age*9)*.035)
            if e.flash>0: body.setColorScale(2.5,2.5,2.5,1)
            elif e.telegraph>0: body.setColorScale(1.9,1.2,.55,1)
            else: body.clearColorScale()
            bar.setScale(e.radius*1.8*max(.01,e.hp/e.max_hp),.05,.075)
            if e.hp>=e.max_hp and not e.telegraph: bar.hide()
            else: bar.show()
        alive={p.uid for p in game.projectiles}
        for uid in list(self.projectile_nodes):
            if uid not in alive: self.projectile_nodes.pop(uid).removeNode()
        for p in game.projectiles:
            if p.uid not in self.projectile_nodes:
                c=(1,.45,.12) if p.friendly else (1,.16,.33)
                node=crystal(self.actors,p.pos,(.22,.22,.22) if p.friendly else (.17,.17,.17),c)
                node.setLightOff()
                self.projectile_nodes[p.uid]=node
            node=self.projectile_nodes[p.uid]
            node.setPos(*p.pos);node.setH(node.getH()+dt*210)
        alive={f.uid for f in game.fields}
        for uid in list(self.field_nodes):
            if uid not in alive: self.field_nodes.pop(uid).removeNode()
        for f in game.fields:
            if f.uid not in self.field_nodes:
                node=self.actors.attachNewNode("solar")
                for r in (1,.7,.35): ring(node,(0,0,.07),f.radius*r,(1,.35,.08),3)
                for i in range(8):
                    a=i*math.tau/8
                    crystal(node,(math.cos(a)*f.radius*.6,math.sin(a)*f.radius*.6,.3),(.12,.12,.4),(1,.5,.16))
                node.setPos(f.x,f.y,0)
                self.field_nodes[f.uid]=node
            self.field_nodes[f.uid].setH(f.life*25)
        for effect in list(self.effects):
            effect[1]-=dt
            if effect[1]<=0:
                effect[0].removeNode();self.effects.remove(effect)
            else:
                node,life,total,expand=effect
                node.setColorScale(1,1,1,min(1,life/total*2))
                if expand: node.setScale(1+(1-life/total)*expand)

    def effect(self,node,life,expand=0):
        node.setTransparency(TransparencyAttrib.MAlpha)
        self.effects.append([node,life,life,expand])

    def event(self,event):
        kind=event["kind"]
        if kind=="beam":
            start=event["start"]
            self.effect(line(self.actors,[(start[0],start[1],start[2]-.13),event["end"]],event["color"],2),.09)
            self.effect(crystal(self.actors,event["end"],(.12,.12,.12),event["color"]),.13,2)
        elif kind in ("kill","spawn","burst","explosion"):
            color=event.get("color",(1,.45,.12))
            pos=event["pos"]
            self.effect(ring(self.actors,pos,.5,color,3),.42,event.get("radius",3)*2)
            if kind!="spawn":
                for i in range(5):
                    a=i*math.tau/5
                    self.effect(crystal(self.actors,(pos[0]+math.cos(a)*.4,pos[1]+math.sin(a)*.4,pos[2]),(.12,.12,.25),color),.35,3)


def make_weapon(parent,index):
    root=parent.attachNewNode("weapon")
    c=WEAPONS[index]["color"]
    dark=(.16,.21,.28)
    length=[.62,.9,.85,1.15,1][index]
    width=[.14,.25,.19,.17,.33][index]
    box(root,(0,.03,-.1),(.13,.22,.3),dark).setP(-16)
    box(root,(0,length*.25,.05),(width,length*.7,.18),(.3,.38,.46))
    box(root,(0,length*.65,.08),(width*.68,length*.4,.105),dark)
    box(root,(0,length*.35,.15),(width*.7,length*.45,.035),c)
    box(root,(0,length*.08,.2),(.05,.08,.07),dark)
    box(root,(0,length*.62,.17),(.035,.05,.07),c)
    if index==1:
        for s in (-1,1): box(root,(s*.08,length*.65,.07),(.075,.4,.1),dark)
    elif index==2:
        box(root,(0,.17,-.15),(.12,.16,.28),(.24,.32,.4)).setP(-12)
    elif index==3:
        for s in (-1,1): box(root,(s*.1,.65,.07),(.06,.7,.08),c)
    elif index==4:
        crystal(root,(0,.6,.09),(.18,.3,.18),c)
        for s in (-1,1): box(root,(s*.2,.6,.04),(.06,.65,.12),dark)
    # Gloved hands are part of the procedural view model.
    box(root,(0,-.03,-.25),(.18,.25,.16),(.085,.11,.16))
    if index>0: box(root,(-.1,.38,-.13),(.19,.23,.15),(.085,.11,.16))
    root.flattenStrong()
    return root
