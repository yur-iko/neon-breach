"""Minimal PyInstaller Windows directory build; no SDK or unused engine plugins."""
from pathlib import Path
import panda3d

root=Path(SPECPATH)
panda=Path(panda3d.__file__).parent
binaries=[(str(panda/name),"panda3d") for name in
          ("libpandagl.dll","libp3windisplay.dll","libp3openal_audio.dll")]
datas=[(str(root/"assets"),"assets"),(str(panda/"etc"),"panda3d/etc"),
       (str(panda/"models"/"gui"),"panda3d/models/gui"),
       (str(panda/"models"/"cmss12.egg.pz"),"panda3d/models")]
a=Analysis([str(root/"main.py")],pathex=[str(root)],binaries=binaries,datas=datas,
           hiddenimports=["panda3d.core","panda3d.direct"],
           excludes=["tkinter","numpy","pandas","matplotlib","PIL","pytest","setuptools","panda3d.bullet","panda3d.ai"],
           noarchive=False)
pyz=PYZ(a.pure)
exe=EXE(pyz,a.scripts,[],exclude_binaries=True,name="NeonBreach",debug=False,
        bootloader_ignore_signals=False,strip=False,upx=False,console=False,
        disable_windowed_traceback=False)
coll=COLLECT(exe,a.binaries,a.datas,strip=False,upx=False,name="NeonBreach")
