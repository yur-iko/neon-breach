"""Generate original compact effects; only Python's standard library is needed."""
import math
import random
import struct
import wave
from pathlib import Path


def generate(folder):
    folder=Path(folder)
    folder.mkdir(parents=True,exist_ok=True)
    rng=random.Random(78)
    sounds={"shot0":(.16,280),"shot1":(.28,95),"shot2":(.11,160),"shot3":(.36,700),"shot4":(.35,85),"special":(.42,440),"hit":(.055,950),"kill":(.18,520),"hurt":(.2,90),"reload":(.25,220),"purchase":(.32,620),"stage":(.6,330)}
    for name,(duration,freq) in sounds.items():
        samples=[]
        count=int(22050*duration)
        for i in range(count):
            t=i/22050
            q=i/count
            envelope=(1-q)**2*min(1,t*600)
            noise=rng.uniform(-1,1)
            tone=math.sin(math.tau*freq*t*(1-.55*q))
            if name.startswith("shot") or name=="hurt": value=(tone*.55+noise*.45)*envelope
            elif name=="reload": value=noise*envelope*(1 if q<.15 or .6<q<.8 else .07)
            else: value=(tone+.3*math.sin(math.tau*freq*1.5*t))*envelope*.65
            samples.append(struct.pack("<h",int(max(-1,min(1,value))*.65*32767)))
        with wave.open(str(folder/(name+".wav")),"wb") as f:
            f.setparams((1,2,22050,count,"NONE","not compressed"))
            f.writeframes(b"".join(samples))


if __name__=="__main__": generate(Path(__file__).parent/"assets")
