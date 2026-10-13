"""Small, editable content tables. Distances are metres and times are seconds."""

TITLE = "NEON BREACH"
WEAPONS = [
    dict(name="ARC PISTOL", short="Pistol", unlock=1, damage=27, interval=.29, magazine=12, reload=1.05, spread=.008, pellets=1, cooldown=7, ability="LANCE SHOT", hint="A charged beam pierces every target", color=(.15,.85,1)),
    dict(name="BREAKER", short="Shotgun", unlock=2, damage=13, interval=.8, magazine=6, reload=1.6, spread=.09, pellets=9, cooldown=9, ability="REPULSOR", hint="A wide blast pushes nearby enemies away", color=(1,.65,.16)),
    dict(name="PULSE RIFLE", short="Rifle", unlock=3, damage=16, interval=.115, magazine=30, reload=1.5, spread=.027, pellets=1, cooldown=14, ability="OVERDRIVE", hint="Four seconds of rapid fire without ammo cost", color=(.3,1,.55)),
    dict(name="NEEDLE", short="Railgun", unlock=5, damage=110, interval=1.1, magazine=4, reload=1.85, spread=0, pellets=1, cooldown=12, ability="ARC NETWORK", hint="A powerful shot chains to visible nearby enemies", color=(.8,.42,1)),
    dict(name="SUNFORGE", short="Launcher", unlock=7, damage=82, interval=.85, magazine=5, reload=1.75, spread=0, pellets=1, cooldown=13, ability="SOLAR WELL", hint="A projectile leaves a burning, slowing field", color=(1,.3,.18)),
]

# id, title, cost, cap, explanation
UPGRADES = [
    ("health", "REINFORCED CORE", 65, 5, "+25 maximum health"),
    ("armor", "ABLATIVE SHELL", 85, 4, "8% less incoming damage per rank"),
    ("speed", "VECTOR BOOTS", 70, 3, "+8% movement and sprint speed"),
    ("damage", "POWER AMPLIFIER", 95, 5, "+12% damage with every weapon"),
    ("reload", "QUICK FEED", 65, 4, "12% faster reloads per rank"),
    ("magazine", "DEEP CELLS", 70, 4, "+20% magazine capacity per rank"),
    ("cooldown", "THERMAL LOOP", 85, 4, "12% shorter ability cooldowns per rank"),
    ("heal", "SALVAGE REPAIR", 95, 3, "Recover 2 health per kill per rank"),
    ("pistol", "PHASE ROUNDS", 100, 1, "Pistol primary fire pierces targets"),
    ("shotgun", "HEAVY BUCKSHOT", 95, 3, "+2 pellets and stronger knockback per rank"),
    ("rifle", "EXTENDED SURGE", 100, 3, "+1.5 seconds of rifle overdrive per rank"),
    ("rail", "CHAIN REACTOR", 115, 3, "+1 arc target and +15% rail damage per rank"),
    ("blast", "STAR BLOOM", 105, 3, "+20% explosion and solar field radius per rank"),
    ("field", "SLOW BURN", 95, 3, "+1.5 seconds of solar field duration per rank"),
    ("aim", "GYRO STABILIZER", 60, 3, "20% less weapon spread per rank"),
]

ENEMIES = {
    "hunter": dict(hp=62, speed=2.8, damage=12, radius=.52, height=1.8, reward=9, color=(.94,.32,.25)),
    "ranger": dict(hp=75, speed=2.1, damage=11, radius=.55, height=2.05, reward=12, color=(1,.69,.17)),
    "flanker": dict(hp=44, speed=4.8, damage=9, radius=.42, height=1.2, reward=10, color=(.65,.35,1)),
    "heavy": dict(hp=220, speed=1.35, damage=20, radius=.8, height=2.6, reward=23, color=(.3,.78,.65)),
    "boss": dict(hp=2600, speed=1.1, damage=19, radius=1.25, height=3.8, reward=250, color=(1,.22,.36)),
}

# x, y, half-width, half-depth, height
ARENAS = [
    dict(name="RELAY YARD", subtitle="Cold machinery. Hot circuits.", color=(.1,.8,1),
         boxes=[(-8,-7,2.2,3,3), (8,-7,2.2,3,3), (-8,7,2.2,3,3), (8,7,2.2,3,3), (0,0,3,2,2.4), (-15,0,1.3,3.5,4), (15,0,1.3,3.5,4)]),
    dict(name="FOUNDRY", subtitle="Stay moving. The furnace is awake.", color=(1,.43,.12),
         boxes=[(-10,-6,1.5,7,3.5),(10,6,1.5,7,3.5),(0,-9,3,1.5,2.6),(0,9,3,1.5,2.6),(-5,3,2,2,3),(5,-3,2,2,3),(-16,12,1.5,2.5,4),(16,-12,1.5,2.5,4)]),
    dict(name="ION GARDEN", subtitle="The signal grows stronger.", color=(.65,.38,1),
         boxes=[(-7,-7,2,2,3.2),(7,-7,2,2,3.2),(-7,7,2,2,3.2),(7,7,2,2,3.2),(0,0,1.8,1.8,5),(-15,0,3,1.2,2.8),(15,0,3,1.2,2.8),(0,14,3,1.2,2.8)]),
]
STAGE_COUNTS = [12,16,20,24,28,32,36,40,44,22]
SPAWNS = [(-18,-17),(18,-17),(-18,17),(18,17),(0,19),(-19,0),(19,0)]
