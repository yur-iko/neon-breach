"""Neon Breach: a portable, offline Python FPS."""
import argparse
import json
import math
import os
from pathlib import Path
import sys
import time

if "--offline-check" in sys.argv:
    def deny_network(event,args):
        if event in ("socket.connect","socket.connect_ex","socket.getaddrinfo","socket.sendto","socket.bind"):
            raise PermissionError("Network access disabled for offline validation")
    sys.addaudithook(deny_network)

from panda3d.core import loadPrcFileData

loadPrcFileData("neon", """
window-title Neon Breach
win-size 1280 720
win-fixed-size false
sync-video true
show-frame-rate-meter false
framebuffer-multisample false
textures-power-2 none
audio-library-name p3openal_audio
notify-level warning
default-directnotify-level warning
model-cache-dir
win-origin -2 -2
""")

from panda3d.core import (Filename, Fog, TextNode, WindowProperties,
                         TransparencyAttrib, Vec4, ClockObject)
from direct.showbase.ShowBase import ShowBase
from direct.gui.DirectGui import DirectFrame, DirectButton, DirectSlider, DGG
from direct.gui.OnscreenText import OnscreenText
from content import TITLE, WEAPONS, UPGRADES, ARENAS, ENEMIES
from simulation import Game, Storage, clamp
from visuals import Scene, make_weapon, box, line, crystal

ROOT=Path(getattr(sys,"_MEIPASS",Path(__file__).resolve().parent))
INK=(.035,.055,.09,1)
PANEL=(.055,.085,.13,.97)
CYAN=(.2,.88,1,1)
WHITE=(.9,.95,1,1)
MUTED=(.52,.66,.77,1)
AMBER=(1,.68,.25,1)


class NeonBreach(ShowBase):
    def __init__(self,save_dir=None,offscreen=False,test_mode=False):
        if offscreen:
            loadPrcFileData("test","window-type offscreen\naudio-library-name null\nsync-video false")
        super().__init__()
        self.disableMouse()
        self.setBackgroundColor(.028,.047,.085)
        self.camLens.setNearFar(.045,140)
        self.camLens.setFov(88)
        self.test_mode=test_mode
        self.offscreen=offscreen
        self.font=self.loader.loadFont(Filename.fromOsSpecific(str(ROOT/"assets"/"Rajdhani-Medium.ttf")).getFullpath())
        self.font.setPixelsPerUnit(80)
        DGG.setDefaultFont(self.font)
        self.storage=Storage(save_dir or Path(os.getenv("LOCALAPPDATA",str(Path.home())))/"NeonBreach")
        self.settings=self.load_settings()
        self.display_mode="windowed"
        self.game=Game(int(time.time()))
        self.checkpoint=None
        self.saved=None
        self.load_saved()
        self.screen=None
        self.screen_name=""
        self.keys={}
        self.captured=False
        self.mouse_warmup=0
        self.recoil=0
        self.muzzle_time=0
        self.hit_flash=0
        self.hurt_flash=0
        self.notice_time=0
        self.last_weapon=-1
        self.view_weapon=None
        self.bob=0
        self.elapsed=0
        self.shot_sounds={}
        self.scene=Scene(self.render)
        self.scene.build(0)
        fog=Fog("distance-haze")
        fog.setColor(.028,.047,.085)
        fog.setLinearRange(30,95)
        self.render.setFog(fog)
        self.create_hud()
        self.load_audio()
        self.bind_controls()
        self.show_main()
        self.taskMgr.add(self.update,"neon-update")
        if not offscreen and not test_mode:
            self.set_display_mode(self.settings["display_mode"])

    def load_settings(self):
        defaults=dict(sensitivity=.13,volume=.65,display_mode="fullscreen")
        data=self.storage.read("settings")
        if isinstance(data,dict):
            for key,low,high in [("sensitivity",.04,.35),("volume",0,1)]:
                v=data.get(key)
                if isinstance(v,(int,float)) and math.isfinite(v): defaults[key]=clamp(v,low,high)
            if data.get("display_mode") in ("fullscreen","windowed"):
                defaults["display_mode"]=data["display_mode"]
        return defaults

    def load_saved(self):
        self.saved=self.storage.read("run")
        if self.saved:
            if isinstance(self.saved,dict) and self.saved.get("completed"):
                self.saved=None
                return
            try:
                verify=Game()
                verify.restore(self.saved)
            except (ValueError,TypeError,KeyError):
                self.saved=None
                self.storage.error="Saved run is invalid. Start a new run to replace it."

    def load_audio(self):
        for name in [*("shot"+str(i) for i in range(5)),"special","hit","kill","hurt","reload","purchase","stage"]:
            path=ROOT/"assets"/(name+".wav")
            if path.exists(): self.shot_sounds[name]=self.loader.loadSfx(Filename.fromOsSpecific(str(path)))
        self.apply_volume()

    def apply_volume(self):
        for sound in self.shot_sounds.values(): sound.setVolume(self.settings["volume"]*.65)

    def sound(self,name):
        sound=self.shot_sounds.get(name)
        if sound: sound.play()

    def text(self,parent,text,x,z,size=.04,color=WHITE,align=TextNode.ALeft):
        return OnscreenText(parent=parent,text=text,pos=(x,z),scale=max(size,.042),fg=color,font=self.font,align=align,mayChange=True)

    def frame(self,parent,bounds,color):
        return DirectFrame(parent=parent,frameSize=bounds,frameColor=color,relief=DGG.FLAT)

    def button(self,parent,text,x,z,width,command,args=None,height=.105,color=None):
        return DirectButton(parent=parent,text=text,pos=(x,0,z),scale=1,
            frameSize=(-width/2,width/2,-height/2,height/2),
            frameColor=[color or (.085,.15,.22,1),(.12,.32,.4,1),(.1,.23,.31,1),(.08,.1,.14,1)],
            text_scale=.048,text_fg=WHITE,text_pos=(0,-.015),text_align=TextNode.ACenter,
            relief=DGG.FLAT,command=command,extraArgs=args or [],pressEffect=False)

    def clear_screen(self):
        if self.screen: self.screen.destroy()
        self.screen=DirectFrame(parent=self.aspect2d,frameColor=(0,0,0,0),frameSize=(-1.78,1.78,-1,1),relief=None)
        return self.screen

    def release_mouse(self):
        self.captured=False
        self.keys.clear()
        if not self.offscreen:
            props=WindowProperties();props.setCursorHidden(False);props.setMouseMode(WindowProperties.MAbsolute)
            self.win.requestProperties(props)

    def capture_mouse(self):
        self.keys.clear()
        if not self.offscreen and not self.test_mode:
            props=WindowProperties();props.setCursorHidden(True);props.setMouseMode(WindowProperties.MConfined)
            self.win.requestProperties(props)
            self.win.movePointer(0,self.win.getXSize()//2,self.win.getYSize()//2)
        self.mouse_warmup=.2
        self.captured=True

    def menu_base(self,name):
        self.screen_name=name
        self.release_mouse()
        self.hud.hide()
        if self.view_weapon: self.view_weapon.hide()
        return self.clear_screen()

    def show_main(self):
        self.game.state="menu"
        root=self.menu_base("main")
        self.frame(root,(-1.78,-.1,-1,1),(.025,.045,.075,.97))
        self.frame(root,(-1.6,-1.55,.43,.78),CYAN)
        self.text(root,"OFFLINE  /  SOLO CAMPAIGN",-1.47,.82,.028,CYAN)
        self.text(root,"NEON",-1.48,.59,.14)
        self.text(root,"BREACH",-1.48,.41,.14)
        self.text(root,"Break the signal. Reclaim the city.",-1.45,.28,.035,MUTED)
        self.button(root,"NEW RUN",-.87,.055,1.16,self.new_prompt,color=(.07,.3,.36,1))
        if self.saved:
            self.button(root,"CONTINUE  /  STAGE "+str(self.saved["stage"]),-.87,-.09,1.16,self.continue_run)
        else:
            self.text(root,"No active checkpoint",-.87,-.105,.032,MUTED,TextNode.ACenter)
        self.button(root,"SETTINGS",-.87,-.235,1.16,self.show_settings)
        self.button(root,"FIELD MANUAL",-.87,-.38,1.16,self.show_controls)
        self.button(root,"EXIT",-.87,-.525,1.16,self.quit_game)
        self.text(root,"10 STAGES     5 WEAPONS     3 ARENAS",-1.45,-.74,.027,CYAN)
        self.text(root,"No network. No accounts. Just you and the breach.",-1.45,-.82,.027,MUTED)
        self.text(root,"PYTHON + PANDA3D  /  v1.0",1.58,-.91,.023,MUTED,TextNode.ARight)
        self.text(root,"SECTOR 01",.22,.79,.035,CYAN)
        self.text(root,"RELAY YARD",.22,.69,.064)
        self.text(root,"A hostile machine signal has taken the district.\nClear all ten sectors and destroy the Warden.",.22,.57,.03,MUTED)
        if self.storage.error: self.text(root,self.storage.error,-1.45,-.92,.026,AMBER)

    def new_prompt(self):
        if self.saved:
            root=self.menu_base("confirm")
            self.frame(root,(-1.1,1.1,-.5,.5),PANEL)
            self.text(root,"START A NEW RUN?",0,.24,.065,WHITE,TextNode.ACenter)
            self.text(root,"This replaces your current campaign checkpoint.",0,.08,.035,MUTED,TextNode.ACenter)
            self.button(root,"START NEW RUN",-.5,-.18,.85,self.new_run)
            self.button(root,"CANCEL",.5,-.18,.85,self.show_main)
        else: self.new_run()

    def new_run(self):
        self.game=Game(int(time.time()))
        self.game.state="menu"
        self.show_controls(deploy=True)

    def show_controls(self,deploy=False):
        root=self.menu_base("controls-deploy" if deploy else "controls")
        self.frame(root,(-1.48,1.48,-.87,.88),PANEL)
        self.text(root,"FIELD MANUAL",-1.25,.65,.07)
        self.text(root,"Keep moving. Break line of sight. Spend salvage between stages.",-1.25,.52,.035,CYAN)
        rows=[("W A S D", "Move"),("MOUSE", "Look around"),("SHIFT", "Sprint"),("LEFT MOUSE", "Fire / hold for automatic fire"),("RIGHT MOUSE", "Aim down sights"),("Q", "Weapon special ability"),("R", "Reload  /  unlimited reserve cells"),("1 - 5 / WHEEL", "Switch unlocked weapons"),("ESC", "Pause and release the mouse"),("F11", "Toggle fullscreen")]
        for i,(key,value) in enumerate(rows):
            z=.36-i*.088
            self.text(root,key,-1.22,z,.031,CYAN)
            self.text(root,value,-.63,z,.032)
        self.text(root,"SURVIVE THE BREACH",.53,.32,.035,AMBER)
        self.text(root,"Glowing enemies are about to attack.\nRed bolts can be dodged.\nSolid cover blocks damage.\n\nHealth and ammo refill each stage.\nEvery cleared stage earns salvage.\n\nWeapons unlock at stages 1, 2, 3, 5, 7.\nContinue resumes a stage checkpoint.",.53,.22,.03,MUTED)
        self.button(root,"DEPLOY  /  CAPTURE MOUSE" if deploy else "BACK",0,-.68,1.3,self.begin_new if deploy else self.show_main)

    def begin_new(self):
        self.game.start_stage(1)
        self.checkpoint=self.game.snapshot()
        self.persist(self.checkpoint)
        self.enter_stage()

    def continue_run(self):
        if not self.saved: return
        self.game=Game()
        self.game.restore(self.saved)
        self.checkpoint=self.saved.copy()
        if self.game.state=="shop":
            self.scene.build(self.game.arena.index)
            self.show_shop()
        else: self.enter_stage()

    def enter_stage(self):
        self.scene.build(self.game.arena.index)
        self.last_weapon=-1
        self.hurt_flash=0
        self.hit_flash=0
        self.game.state="playing"
        self.resume()
        unlocked=[w["name"] for w in WEAPONS if w["unlock"]==self.game.stage]
        self.notice("STAGE %02d  /  %s%s"%(self.game.stage,ARENAS[self.game.arena.index]["name"],"   |   "+unlocked[0]+" ONLINE" if unlocked else ""),5)
        self.sound("stage")

    def persist(self,data):
        if self.storage.write("run",data): self.saved=data
        elif hasattr(self,"notice_label"): self.notice(self.storage.error,6)

    def resume(self):
        self.screen_name="play"
        if self.screen: self.screen.destroy();self.screen=None
        self.game.state="playing"
        self.hud.show()
        if self.view_weapon: self.view_weapon.show()
        self.capture_mouse()

    def pause(self):
        if self.game.state!="playing": return
        self.game.state="paused"
        root=self.menu_base("pause")
        self.frame(root,(-.78,.78,-.66,.67),PANEL)
        self.text(root,"SIGNAL PAUSED",0,.43,.066,WHITE,TextNode.ACenter)
        self.text(root,"Mouse released. Your checkpoint is saved.",0,.28,.029,MUTED,TextNode.ACenter)
        self.button(root,"RESUME  /  CAPTURE MOUSE",0,.09,1.25,self.resume)
        self.button(root,"SETTINGS",0,-.08,1.25,self.show_settings)
        self.button(root,"MAIN MENU",0,-.25,1.25,self.show_main)
        self.button(root,"EXIT GAME",0,-.42,1.25,self.quit_game)

    def escape(self):
        if self.game.state=="playing": self.pause()
        elif self.screen_name=="pause": self.resume()
        elif self.screen_name=="settings": self.leave_settings()
        elif self.screen_name in ("controls","confirm"): self.show_main()

    def show_settings(self):
        self.settings_return="pause" if self.screen_name=="pause" else "main"
        root=self.menu_base("settings")
        self.frame(root,(-1.05,1.05,-.8,.82),PANEL)
        self.text(root,"SETTINGS",-.85,.63,.07)
        self.sens_label=self.text(root,"",-.82,.4,.037)
        self.sens_slider=DirectSlider(parent=root,pos=(.03,0,.25),scale=.77,range=(.04,.35),value=self.settings["sensitivity"],pageSize=.01,command=self.change_settings)
        self.volume_label=self.text(root,"",-.82,.07,.037)
        self.volume_slider=DirectSlider(parent=root,pos=(.03,0,-.08),scale=.77,range=(0,1),value=self.settings["volume"],pageSize=.05,command=self.change_settings)
        self.display_button=self.button(root,"DISPLAY: "+self.display_mode.upper(),0,-.3,1.64,self.toggle_fullscreen)
        self.text(root,"F11 or Alt+Enter switches modes. Your choice is saved.",-.82,-.49,.028,MUTED)
        self.button(root,"BACK",0,-.65,.8,self.leave_settings)
        self.change_settings()

    def change_settings(self):
        if not hasattr(self,"sens_slider") or not hasattr(self,"volume_slider"): return
        self.settings["sensitivity"]=float(self.sens_slider["value"])
        self.settings["volume"]=float(self.volume_slider["value"])
        self.sens_label.setText("MOUSE SENSITIVITY    %.2f"%self.settings["sensitivity"])
        self.volume_label.setText("EFFECTS VOLUME    %d%%"%round(self.settings["volume"]*100))
        self.apply_volume()

    def leave_settings(self):
        self.storage.write("settings",self.settings)
        if self.settings_return=="pause":
            self.game.state="playing"
            self.pause()
        else: self.show_main()

    def show_shop(self):
        self.game.state="shop"
        root=self.menu_base("shop")
        self.frame(root,(-1.78,1.78,-1,1),(.025,.045,.07,.985))
        self.text(root,"SECTOR CLEAR",-1.59,.8,.065)
        self.text(root,"STAGE %02d  /  UPGRADE BAY"%self.game.stage,-1.58,.7,.03,CYAN)
        self.text(root,"%d SALVAGE"%self.game.credits,1.57,.81,.05,AMBER,TextNode.ARight)
        self.text(root,"Full repair and fresh cells on deployment",1.57,.7,.028,MUTED,TextNode.ARight)
        for i,(key,title,_,cap,desc) in enumerate(UPGRADES):
            col,row=i//5,i%5
            x=-1.59+col*1.08
            z=.53-row*.247
            rank=self.game.upgrades[key]
            panel=self.frame(root,(x,x+1.02,z-.21,z+.025),(.055,.09,.135,1))
            self.text(panel,title,x+.05,z-.025,.029,CYAN if rank<cap else AMBER)
            self.text(panel,desc,x+.05,z-.074,.031,MUTED)
            self.text(panel,"%d / %d"%(rank,cap),x+.05,z-.16,.027)
            cost=self.game.cost(i)
            label="MAXED" if rank>=cap else "%d  /  BUY"%cost
            btn=self.button(panel,label,x+.73,z-.15,.47, self.purchase,[i],height=.071)
            if rank>=cap or cost>self.game.credits: btn["state"]=DGG.DISABLED
        next_stage=self.game.stage+1
        unlock=[w["name"] for w in WEAPONS if w["unlock"]==next_stage]
        self.text(root,"NEXT  /  "+ARENAS[(next_stage-1)%3]["name"]+("    + "+unlock[0] if unlock else ""),-1.58,-.86,.029,CYAN)
        self.button(root,"SAVE & MENU",.48,-.85,.69,self.show_main)
        self.button(root,"DEPLOY STAGE %02d"%next_stage,1.23,-.85,.73,self.next_stage,color=(.055,.31,.36,1))

    def purchase(self,index):
        if self.game.buy(index):
            self.sound("purchase")
            self.persist(self.game.snapshot())
            self.show_shop()

    def next_stage(self):
        self.game.start_stage(self.game.stage+1)
        self.checkpoint=self.game.snapshot()
        self.persist(self.checkpoint)
        self.enter_stage()

    def retry(self):
        self.game.restore(self.checkpoint)
        self.enter_stage()

    def show_end(self,victory):
        root=self.menu_base("victory" if victory else "dead")
        self.frame(root,(-1.15,1.15,-.71,.72),PANEL)
        self.text(root,"SIGNAL BROKEN" if victory else "CORE OFFLINE",0,.45,.087,CYAN if victory else AMBER,TextNode.ACenter)
        self.text(root,"The Warden is down. The district is yours." if victory else "Reboot from the start of this stage and try again.",0,.29,.034,MUTED,TextNode.ACenter)
        self.text(root,"%d ELIMINATIONS    /    %02d:%02d ACTIVE TIME"%(self.game.kills,int(self.game.total_time)//60,int(self.game.total_time)%60),0,.09,.033,WHITE,TextNode.ACenter)
        if victory:
            self.storage.write("run",dict(version=1,completed=True))
            self.saved=None
            self.button(root,"NEW RUN",0,-.13,1.3,self.new_run)
        else: self.button(root,"RETRY STAGE %02d"%self.game.stage,0,-.13,1.3,self.retry)
        self.button(root,"MAIN MENU",0,-.3,1.3,self.show_main)
        self.button(root,"EXIT",0,-.47,1.3,self.quit_game)

    def create_hud(self):
        self.hud=DirectFrame(parent=self.aspect2d,frameColor=(0,0,0,0),relief=None)
        self.frame(self.hud,(-1.71,-.8,.73,.94),(.02,.04,.07,.86))
        self.stage_label=self.text(self.hud,"",-1.61,.845,.034,CYAN)
        self.arena_label=self.text(self.hud,"",-1.61,.783,.027,MUTED)
        self.frame(self.hud,(.9,1.71,.73,.94),(.02,.04,.07,.86))
        self.threat_label=self.text(self.hud,"",1.61,.843,.036,WHITE,TextNode.ARight)
        self.credit_label=self.text(self.hud,"",1.61,.782,.028,AMBER,TextNode.ARight)
        self.frame(self.hud,(-1.71,-.87,-.92,-.65),(.02,.04,.07,.92))
        self.health_label=self.text(self.hud,"",-1.6,-.743,.06)
        self.frame(self.hud,(-1.6,-.99,-.833,-.809),(.23,.15,.2,1))
        self.health_bar=self.frame(self.hud,(-1.6,-.99,-.833,-.809),CYAN)
        self.text(self.hud,"CORE INTEGRITY",-1.6,-.885,.023,MUTED)
        self.frame(self.hud,(.67,1.71,-.92,-.62),(.02,.04,.07,.92))
        self.weapon_label=self.text(self.hud,"",.77,-.697,.031,CYAN)
        self.ammo_label=self.text(self.hud,"",1.6,-.77,.062,WHITE,TextNode.ARight)
        self.ability_label=self.text(self.hud,"",.77,-.868,.025,AMBER)
        self.slot_label=self.text(self.hud,"",-.08,-.9,.027,MUTED,TextNode.ACenter)
        self.notice_label=self.text(self.hud,"",0,.61,.036,WHITE,TextNode.ACenter)
        self.boss_label=self.text(self.hud,"",0,.82,.031,AMBER,TextNode.ACenter)
        self.reticle=self.hud.attachNewNode("reticle")
        for a,b in [((-.019,0,0),(-.007,0,0)),((.007,0,0),(.019,0,0)),((0,0,-.019),(0,0,-.007)),((0,0,.007),(0,0,.019))]:
            line(self.reticle,[a,b],(.8,1,1),1.6)
        self.hit_label=self.text(self.hud,"",0,-.015,.055,AMBER,TextNode.ACenter)
        self.damage_overlay=self.frame(self.hud,(-1.78,1.78,-1,1),(.8,.05,.12,0))
        self.damage_overlay.setTransparency(TransparencyAttrib.MAlpha)
        self.text(self.hud,"SHIFT sprint   RMB aim   Q ability   R reload   ESC pause",0,-.974,.022,MUTED,TextNode.ACenter)

    def notice(self,text,duration=3):
        self.notice_label.setText(text)
        self.notice_time=duration

    def bind_controls(self):
        for key in ("w","a","s","d","shift","mouse1","mouse3"):
            self.accept(key,self.key,[key,True])
            self.accept(key+"-up",self.key,[key,False])
        self.accept("q",self.special)
        self.accept("r",lambda:self.game.reload())
        self.accept("escape",self.escape)
        self.accept("f11",self.toggle_fullscreen)
        self.accept("alt-enter",self.toggle_fullscreen)
        for i in range(5): self.accept(str(i+1),self.select_weapon,[i])
        self.accept("wheel_up",self.cycle_weapon,[1])
        self.accept("wheel_down",self.cycle_weapon,[-1])
        self.accept("window-event",self.window_event)

    def key(self,key,value):
        if self.game.state=="playing" and self.captured: self.keys[key]=value

    def special(self):
        if self.game.state=="playing":
            if not self.game.shoot(True) and self.game.cooldowns[self.game.weapon]>0: self.notice("ABILITY COOLING  /  %.1fs"%self.game.cooldowns[self.game.weapon],1)

    def select_weapon(self,index):
        if self.game.state=="playing":
            if index not in self.game.unlocked: self.notice("UNLOCKS AT STAGE %d"%WEAPONS[index]["unlock"],2)
            else: self.game.switch(index)

    def cycle_weapon(self,amount):
        if self.game.state=="playing":
            unlocked=self.game.unlocked
            self.game.switch(unlocked[(unlocked.index(self.game.weapon)+amount)%len(unlocked)])

    def toggle_fullscreen(self):
        if self.offscreen: return
        self.set_display_mode("windowed" if self.display_mode=="fullscreen" else "fullscreen")

    def monitor_bounds(self):
        """Use the current monitor's desktop bounds without changing its video mode."""
        if sys.platform=="win32":
            import ctypes
            from ctypes import wintypes
            class MonitorInfo(ctypes.Structure):
                _fields_=[("size",wintypes.DWORD),("monitor",wintypes.RECT),
                          ("work",wintypes.RECT),("flags",wintypes.DWORD)]
            user32=ctypes.WinDLL("user32",use_last_error=True)
            user32.MonitorFromWindow.argtypes=[wintypes.HWND,wintypes.DWORD]
            user32.MonitorFromWindow.restype=wintypes.HANDLE
            user32.GetMonitorInfoW.argtypes=[wintypes.HANDLE,ctypes.POINTER(MonitorInfo)]
            user32.GetMonitorInfoW.restype=wintypes.BOOL
            monitor=user32.MonitorFromWindow(self.win.getWindowHandle().getIntHandle(),2)
            info=MonitorInfo();info.size=ctypes.sizeof(info)
            if user32.GetMonitorInfoW(monitor,ctypes.byref(info)):
                r=info.monitor
                return r.left,r.top,r.right-r.left,r.bottom-r.top
        return 0,0,self.pipe.getDisplayWidth(),self.pipe.getDisplayHeight()

    def set_display_mode(self,mode):
        if self.offscreen: return
        left,top,width,height=self.monitor_bounds()
        fullscreen=mode=="fullscreen"
        props=WindowProperties()
        # Borderless desktop fullscreen avoids exclusive-mode driver transitions.
        props.setFullscreen(False)
        props.setUndecorated(fullscreen)
        props.setFixedSize(False)
        if fullscreen:
            props.setSize(width,height)
            props.setOrigin(left,top)
        else:
            w,h=min(1280,max(640,width-80)),min(720,max(360,height-100))
            props.setSize(w,h)
            props.setOrigin(left+(width-w)//2,top+(height-h)//2)
        self.keys.clear()
        self.mouse_warmup=.3
        self.win.requestProperties(props)
        self.display_mode=mode
        self.settings["display_mode"]=mode
        self.storage.write("settings",self.settings)
        if self.screen_name=="settings":
            self.display_button["text"]="DISPLAY: "+mode.upper()

    def window_event(self,window):
        if window != self.win: return
        if not window.getProperties().getOpen():
            self.quit_game()
            return
        super().windowEvent(window)
        aspect=window.getXSize()/max(1,window.getYSize())
        # Keep the 16:9 UI canvas in view, without stretching it on other screens.
        self.aspect2d.setScale(min(9/16,1/aspect),1,min(1,aspect/(16/9)))
        if hasattr(self,"game") and not self.test_mode and self.game.state=="playing" and not window.getProperties().getForeground(): self.pause()

    def handle_events(self):
        events=self.game.events[:]
        self.game.events.clear()
        for event in events:
            self.scene.event(event)
            kind=event["kind"]
            if kind=="shoot":
                self.muzzle_time=.055
                self.sound("special" if event["special"] else "shot"+str(event["weapon"]))
                self.recoil=min(.16,self.recoil+[.06,.14,.035,.12,.12][event["weapon"]])
            elif kind=="hit":
                if self.hit_flash<=0: self.sound("hit")
                self.hit_flash=.1
            elif kind=="hurt": self.hurt_flash=.32;self.sound("hurt")
            elif kind in ("kill","reload","purchase"): self.sound(kind)
            elif kind=="boss": self.notice("WARDEN ONLINE  /  WATCH THE TELEGRAPH",5)
            elif kind=="shop":
                self.persist(self.game.snapshot())
                self.show_shop()
            elif kind=="death": self.show_end(False)
            elif kind=="victory": self.show_end(True)

    def render_play(self,dt):
        g=self.game
        self.camera.setPos(g.x,g.y,1.65)
        self.camera.setHpr(g.yaw,g.pitch,0)
        target=62 if g.aim else 88
        self.camLens.setFov(self.camLens.getHfov()+(target-self.camLens.getHfov())*min(1,dt*12))
        if self.last_weapon!=g.weapon:
            if self.view_weapon: self.view_weapon.removeNode()
            self.view_weapon=make_weapon(self.camera,g.weapon)
            self.view_weapon.setDepthTest(False);self.view_weapon.setDepthWrite(False)
            self.view_weapon.setBin("fixed",5)
            self.view_weapon.setScale(.52)
            self.view_weapon.setFogOff()
            self.view_weapon.setLightOff()
            self.muzzle=crystal(self.view_weapon,(0,[.85,1.12,1.06,1.4,1.23][g.weapon],.08),(.18,.3,.18),WEAPONS[g.weapon]["color"])
            self.last_weapon=g.weapon
        moving=any(self.keys.get(k) for k in ("w","a","s","d"))
        self.bob+=dt*(11 if moving else 2)
        self.recoil=max(0,self.recoil-dt*.6)
        self.view_weapon.show()
        self.view_weapon.setPos(.025 if g.aim else .25,.57-self.recoil,-.16+math.sin(self.bob)*(.009 if moving else .002))
        self.view_weapon.setHpr(0,-self.recoil*60-(25 if g.reload_left else 0),-18 if g.reload_left else 0)
        self.muzzle_time=max(0,self.muzzle_time-dt)
        if self.muzzle_time>0: self.muzzle.show()
        else: self.muzzle.hide()
        self.stage_label.setText("STAGE %02d / 10"%g.stage)
        self.arena_label.setText(ARENAS[g.arena.index]["name"])
        self.threat_label.setText("%02d HOSTILES"%(len(g.enemies)+g.pending+(1 if g.stage==10 and not g.boss_spawned else 0)))
        self.credit_label.setText("%d SALVAGE"%g.credits)
        self.health_label.setText("%03d / %d"%(math.ceil(g.hp),g.max_health))
        self.health_bar["frameSize"]=(-1.6,-1.6+.61*g.hp/g.max_health,-.833,-.809)
        self.health_bar["frameColor"]=CYAN if g.hp>g.max_health*.3 else (1,.22,.3,1)
        self.weapon_label.setText(WEAPONS[g.weapon]["name"])
        self.ammo_label.setText("RELOAD %.1f"%g.reload_left if g.reload_left else "%02d / %02d"%(g.ammo[g.weapon],g.magazine(g.weapon)))
        ready="READY" if g.cooldowns[g.weapon]<=0 else "%.1fs"%g.cooldowns[g.weapon]
        if g.weapon==2 and g.overdrive>0: ready="ACTIVE %.1fs"%g.overdrive
        self.ability_label.setText("Q  %s  /  %s"%(WEAPONS[g.weapon]["ability"],ready))
        self.slot_label.setText("   ".join(("[%d]" if i==g.weapon else " %d ")%(i+1) for i in g.unlocked))
        self.hit_flash=max(0,self.hit_flash-dt)
        self.hurt_flash=max(0,self.hurt_flash-dt)
        self.hit_label.setText("x" if self.hit_flash>0 else "")
        self.damage_overlay["frameColor"]=(.8,.025,.08,self.hurt_flash*.5)
        self.notice_time=max(0,self.notice_time-dt)
        if self.notice_time==0: self.notice_label.setText("")
        boss=next((e for e in g.enemies if e.kind=="boss"),None)
        self.boss_label.setText("WARDEN   %d%%   %s"%(math.ceil(boss.hp/boss.max_hp*100),"CHARGING" if boss.telegraph else "") if boss else "")

    def update(self,task):
        dt=min(.05,ClockObject.getGlobalClock().getDt())
        self.elapsed+=dt
        if self.game.state=="playing":
            if self.captured and not self.offscreen and not self.test_mode:
                pointer=self.win.getPointer(0)
                cx,cy=self.win.getXSize()//2,self.win.getYSize()//2
                dx,dy=pointer.getX()-cx,pointer.getY()-cy
                self.mouse_warmup=max(0,self.mouse_warmup-dt)
                if self.mouse_warmup==0 and abs(dx)<cx and abs(dy)<cy:
                    self.game.yaw-=dx*self.settings["sensitivity"]
                    self.game.pitch=clamp(self.game.pitch-dy*self.settings["sensitivity"],-85,85)
                self.win.movePointer(0,cx,cy)
            self.game.aim=bool(self.keys.get("mouse3"))
            self.game.step(dt,int(bool(self.keys.get("w")))-int(bool(self.keys.get("s"))),int(bool(self.keys.get("d")))-int(bool(self.keys.get("a"))),self.keys.get("shift",False),self.keys.get("mouse1",False))
            self.scene.sync(self.game,dt)
            self.render_play(dt)
            self.handle_events()
        elif self.game.state=="menu":
            self.camera.setPos(15,-20,11)
            self.camera.lookAt(-3,4,1.5)
            self.camLens.setFov(74)
        return task.cont

    def screenshot(self,path):
        for _ in range(4): self.graphicsEngine.renderFrame()
        self.win.saveScreenshot(Filename.fromOsSpecific(str(Path(path).resolve())))

    def quit_game(self):
        self.storage.write("settings",self.settings)
        self.release_mouse()
        self.userExit()


def smoke(app,folder):
    """Exercise real rendered scenes and save state without driving user input."""
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    results=[]
    def check(name,condition):
        results.append(dict(name=name,passed=bool(condition)))
        if not condition: raise AssertionError(name)
    app.camera.setPos(15,-20,11);app.camera.lookAt(-3,4,1.5)
    app.screenshot(folder/"01-menu.png")
    app.new_run();app.screenshot(folder/"02-controls.png")
    app.begin_new()
    g=app.game
    g.spawn("hunter",(-3,-10));g.spawn("ranger",(3,-8))
    g.yaw=0;g.pitch=0
    app.scene.sync(g,0)
    app.render_play(.016)
    app.screenshot(folder/"03-gameplay.png")
    check("new game checkpoint",app.storage.read("run")["stage"]==1)
    g.x=-12;g.y=-15
    before=(g.x,g.y)
    for _ in range(30): g.step(.016,forward=1)
    check("movement changes position",before!=(g.x,g.y))
    app.pause();hp=g.hp;pos=(g.x,g.y)
    for _ in range(60):g.step(.016,forward=1,fire=True)
    check("pause freezes simulation",(g.x,g.y)==pos and g.hp==hp)
    app.screenshot(folder/"04-pause.png")
    app.resume()
    g.enemies=[];g.pending=0;g.step(.016);app.handle_events()
    check("clear stage opens upgrade bay",g.state=="shop")
    g.credits=900
    app.show_shop();app.purchase(0)
    check("purchase saved",app.storage.read("run")["upgrades"]["health"]==1)
    app.screenshot(folder/"05-upgrades.png")
    app.next_stage()
    check("stage two unlock",1 in g.unlocked and g.hp==125)
    g.damage_player(10000);app.handle_events()
    check("death screen",app.screen_name=="dead")
    app.screenshot(folder/"06-death.png")
    app.retry()
    check("retry restores checkpoint",g.stage==2 and g.hp==125 and g.state=="playing")
    app.show_settings();app.screenshot(folder/"07-settings.png");app.leave_settings()
    for stage in (2,3,5,7,10):
        g.start_stage(stage);app.enter_stage()
        g.pending=0
        for i,kind in enumerate(("hunter","ranger","flanker","heavy")):
            g.spawn(kind,(-5+i*3,-9+i*.3))
        if stage==10: g.spawn("boss",(0,9));g.boss_spawned=True
        g.weapon=max(g.unlocked)
        app.scene.sync(g,.016);app.render_play(.016)
        app.screenshot(folder/("stage-%02d.png"%stage))
    g.enemies=[];g.pending=0;g.boss_spawned=True;g.step(.016);app.handle_events()
    check("final stage victory",app.screen_name=="victory")
    app.screenshot(folder/"08-victory.png")
    # Measured render loop, separated from simulated combat checks.
    g.start_stage(8);app.enter_stage()
    for i,kind in enumerate(("hunter","ranger","flanker","heavy")*3):g.spawn(kind,(-18+(i%6)*6,8+(i//6)*7))
    start=time.perf_counter()
    for _ in range(240):
        g.step(1/120);app.scene.sync(g,1/120);app.render_play(1/120);app.handle_events();app.graphicsEngine.renderFrame()
    elapsed=time.perf_counter()-start
    gsg=app.win.getGsg()
    report=dict(checks=results,renderer=gsg.getDriverRenderer(),vendor=gsg.getDriverVendor(),driver=gsg.getDriverVersion(),render_frames=240,render_seconds=elapsed,average_render_fps=240/elapsed,mode="offscreen" if app.offscreen else "onscreen scripted")
    (folder/"smoke-report.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    app.destroy()


def main():
    parser=argparse.ArgumentParser(description="Neon Breach offline FPS")
    parser.add_argument("--save-dir",type=Path)
    parser.add_argument("--smoke-test",type=Path,help="Run a scripted rendering check and write screenshots/report")
    parser.add_argument("--offscreen",action="store_true")
    parser.add_argument("--offline-check",action="store_true",help="Deny Python networking during validation")
    args=parser.parse_args()
    app=NeonBreach(args.save_dir,args.offscreen,bool(args.smoke_test))
    if args.smoke_test: smoke(app,args.smoke_test)
    else: app.run()


if __name__=="__main__":
    try:
        main()
    except Exception:
        import traceback
        log=Path(os.getenv("LOCALAPPDATA",str(Path.cwd())))/"NeonBreach"
        try:
            log.mkdir(parents=True,exist_ok=True)
            (log/"error.log").write_text(traceback.format_exc(),encoding="utf-8")
        except OSError: pass
        raise
