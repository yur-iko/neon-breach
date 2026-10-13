"""Gameplay regression tests. Run with: python -m unittest -v test_game"""
import copy
import math
import tempfile
import unittest
from pathlib import Path
from content import ARENAS, SPAWNS, UPGRADES, WEAPONS
from simulation import Arena, Game, Projectile, Field, Storage, distance


class CombatTests(unittest.TestCase):
    def setUp(self):
        self.g=Game(7)
        self.g.start_stage(7)
        self.g.x,self.g.y=-18,-17
        self.g.pending=0

    def target(self,y=-10,x=-18,kind="heavy"):
        return self.g.spawn(kind,(x,y))

    def tick(self,seconds):
        for _ in range(round(seconds/.02)): self.g.step(.02)

    def fire(self,weapon,special=False):
        self.g.weapon=weapon;self.g.shot_timer=0
        return self.g.shoot(special)

    def test_all_primary_weapons_deal_damage(self):
        for weapon in range(5):
            with self.subTest(weapon=weapon):
                self.g.enemies=[];self.g.projectiles=[];self.g.state="playing"
                enemy=self.target(y=-13)
                hp=enemy.hp
                self.assertTrue(self.fire(weapon))
                self.tick(.25)
                self.assertLess(enemy.hp,hp)

    def test_pistol_special_pierces_multiple_targets(self):
        a=self.target(-12);b=self.target(-8)
        self.fire(0,True)
        self.assertLess(a.hp,a.max_hp);self.assertLess(b.hp,b.max_hp)

    def test_primary_piercing_upgrade(self):
        a=self.target(-12);b=self.target(-8)
        self.g.upgrades["pistol"]=1
        self.g.rng.uniform=lambda a,b:0
        self.fire(0)
        self.assertLess(b.hp,b.max_hp)

    def test_shotgun_special_pushes_and_hurts(self):
        enemy=self.target(-12)
        before=enemy.y
        self.fire(1,True)
        self.assertGreater(enemy.y,before+2)
        self.assertLess(enemy.hp,enemy.max_hp)

    def test_rifle_overdrive_is_faster_and_free(self):
        self.fire(2,True)
        ammo=self.g.ammo[2]
        self.g.shot_timer=0
        self.g.shoot()
        self.assertEqual(self.g.ammo[2],ammo)
        self.assertLess(self.g.shot_timer,WEAPONS[2]["interval"])
        self.assertGreater(self.g.overdrive,0)
        self.g.ammo[2]=0;self.g.shot_timer=0
        self.assertTrue(self.g.shoot())
        self.assertEqual(self.g.ammo[2],0)

    def test_rail_special_chains(self):
        a=self.target(-11)
        b=self.target(-10,x=-15)
        self.fire(3,True)
        self.assertLess(b.hp,b.max_hp)

    def test_launcher_special_creates_damaging_field(self):
        self.target(-12)
        self.fire(4,True)
        self.tick(.3)
        self.assertTrue(self.g.fields)
        f=self.g.fields[0]
        e=self.g.spawn("heavy",(f.x+1,f.y))
        hp=e.hp
        self.tick(.1)
        self.assertLess(e.hp,hp)

    def test_ability_cooldown_prevents_repeat(self):
        self.fire(0,True);self.g.shot_timer=0
        self.assertFalse(self.g.shoot(True))
        self.assertGreater(self.g.cooldowns[0],0)

    def test_reload_and_weapon_switch(self):
        self.g.ammo[0]=0;self.g.weapon=0
        self.g.reload()
        self.assertGreater(self.g.reload_left,0)
        self.g.switch(1)
        self.assertEqual(self.g.reload_left,0)
        self.g.switch(0);self.g.reload()
        # Keep combat active while timer advances.
        self.g.pending=1;self.g.spawn_timer=99
        self.tick(1.2)
        self.assertEqual(self.g.ammo[0],self.g.magazine(0))

    def test_hitscan_cannot_cross_cover(self):
        self.g.x,self.g.y=0,-10
        enemy=self.g.spawn("heavy",(0,6))
        self.fire(3,True)
        self.assertEqual(enemy.hp,enemy.max_hp)

    def test_enemy_projectile_cannot_cross_cover(self):
        self.g.x,self.g.y=0,-10
        e=self.g.spawn("ranger",(0,10))
        self.g.enemy_fire(e)
        hp=self.g.hp
        for _ in range(180):
            self.g.step(.02)
        self.assertEqual(self.g.hp,hp)

    def test_splash_respects_cover(self):
        enemy=self.g.spawn("heavy",(0,3))
        p=Projectile(999,(0,-2.1,1),(0,10,0),100,True)
        self.g.upgrades["blast"]=3
        self.g.explode(p)
        self.assertEqual(enemy.hp,enemy.max_hp)

    def test_projectile_swept_collision(self):
        e=self.target(-12)
        self.g.projectiles=[Projectile(999,(-18,-17,1),(0,1000,0),100,True)]
        self.g.step(.02)
        self.assertLess(e.hp,e.max_hp)

    def test_damage_armor_death_and_no_negative_health(self):
        self.g.upgrades["armor"]=4
        self.g.damage_player(100)
        self.assertAlmostEqual(self.g.hp,32)
        self.g.damage_player(1000)
        self.assertEqual(self.g.state,"dead")
        self.assertEqual(self.g.hp,0)

    def test_kill_reward_and_heal(self):
        self.g.hp=50;self.g.upgrades["heal"]=3
        e=self.target()
        self.g.hit(e,10000)
        self.assertEqual(self.g.hp,56)
        self.assertEqual(self.g.kills,1)
        self.assertGreater(self.g.credits,0)

    def test_solar_field_slows_movement(self):
        a=Game(9);a.start_stage(7);a.x,a.y=-18,-17;a.pending=0
        b=Game(9);b.start_stage(7);b.x,b.y=-18,-17;b.pending=0
        ea=a.spawn("hunter",(-18,-10));eb=b.spawn("hunter",(-18,-10))
        b.fields=[Field(888,-18,-10,5,5)]
        for _ in range(20):a.step(.02);b.step(.02)
        self.assertLess(abs(eb.y+10),abs(ea.y+10)*.6)

    def test_boss_has_two_patterns(self):
        self.g.x,self.g.y=-18,-17
        boss=self.g.spawn("boss",(-18,-8))
        boss.attack=0
        self.tick(1)
        self.assertEqual(boss.phase,1)
        self.assertGreaterEqual(len(self.g.projectiles),10)
        self.g.projectiles=[];boss.attack=0
        self.tick(1)
        self.assertEqual(boss.phase,2)
        self.assertGreater(len(self.g.projectiles),0)


class ProgressionTests(unittest.TestCase):
    def test_complete_ten_stage_loop_and_unlocks(self):
        g=Game();g.start_stage(1)
        visited=[]
        for stage in range(1,11):
            self.assertEqual(g.stage,stage)
            visited.extend(g.unlocked)
            while g.pending:
                e=g.spawn("hunter",(-18,17));g.pending-=1;g.hit(e,10000)
            if stage==10:
                boss=g.spawn("boss",(0,17));g.boss_spawned=True;g.hit(boss,10000)
            g.step(.02)
            self.assertEqual(g.state,"victory" if stage==10 else "shop")
            if stage<10:g.start_stage(stage+1)
        self.assertEqual(set(visited),set(range(5)))
        self.assertGreater(g.credits,3000)

    def test_all_upgrades_purchase_caps_and_costs(self):
        g=Game();g.state="shop";g.credits=100000
        for i,(key,_,_,cap,_) in enumerate(UPGRADES):
            previous=0
            for rank in range(cap):
                cost=g.cost(i);self.assertGreater(cost,previous)
                credits=g.credits
                self.assertTrue(g.buy(i));self.assertEqual(credits-g.credits,cost)
                previous=cost
            self.assertFalse(g.buy(i));self.assertEqual(g.upgrades[key],cap)

    def test_cannot_purchase_without_funds_or_outside_shop(self):
        g=Game();g.state="shop"
        self.assertFalse(g.buy(0))
        g.credits=500;g.state="playing"
        self.assertFalse(g.buy(0))

    def test_upgrade_stats_and_next_stage_refill(self):
        g=Game();g.upgrades["health"]=3;g.upgrades["magazine"]=2
        g.start_stage(5)
        self.assertEqual(g.hp,175)
        self.assertEqual(g.ammo[2],42)

    def test_checkpoint_and_shop_roundtrip(self):
        g=Game();g.start_stage(7);g.credits=395;g.upgrades["rail"]=2;g.weapon=4
        for state in ("playing","shop"):
            g.state=state
            with tempfile.TemporaryDirectory() as folder:
                store=Storage(folder);store.write("run",g.snapshot())
                restored=Game();restored.restore(Storage(folder).read("run"))
                self.assertEqual(restored.stage,7);self.assertEqual(restored.credits,395)
                self.assertEqual(restored.upgrades["rail"],2)
                self.assertEqual(restored.weapon,4)
                self.assertEqual(restored.state,state)

    def test_missing_malformed_and_invalid_saves(self):
        with tempfile.TemporaryDirectory() as folder:
            store=Storage(folder)
            self.assertIsNone(store.read("run"))
            (Path(folder)/"run.json").write_text("{broken",encoding="utf-8")
            self.assertIsNone(store.read("run"));self.assertTrue(store.error)
        g=Game();good=g.snapshot()
        invalid=[None,[],{},dict(good,stage=11),dict(good,stage=True),dict(good,credits=-1),dict(good,total_time=float("nan")),dict(good,state="hacked"),dict(good,upgrades={"health":500})]
        for data in invalid:
            with self.subTest(data=data):
                with self.assertRaises(ValueError): Game().restore(data)


class NavigationTests(unittest.TestCase):
    def test_every_spawn_is_clear_and_connected(self):
        for i in range(3):
            arena=Arena(i);arena.update_flow(0,-18)
            self.assertEqual(set(arena.flow),arena.cells)
            for p in SPAWNS:self.assertTrue(arena.free(*p,.85));self.assertIn(arena.cell(*p),arena.flow)

    def test_collision_slides_and_does_not_tunnel(self):
        arena=Arena(0)
        x,y=arena.move(0,-10,0,30)
        self.assertLess(y,-2.3)
        self.assertTrue(arena.free(x,y))
        x,y=arena.move(0,-10,200,0)
        self.assertLess(x,22)
        self.assertTrue(arena.free(x,y))

    def test_enemy_routes_reach_player_from_all_spawns(self):
        for arena in range(3):
            for spawn in SPAWNS:
                with self.subTest(arena=arena,spawn=spawn):
                    g=Game();g.start_stage(arena+1);g.pending=1;g.spawn_timer=1000
                    g.hp=100000
                    e=g.spawn("hunter",spawn)
                    for _ in range(1500):g.step(.04)
                    self.assertLess(distance((e.x,e.y),(g.x,g.y)),2)

    def test_ranged_enemy_telegraphs_before_firing(self):
        g=Game();g.start_stage(2);g.pending=0;g.x,g.y=-18,-17
        e=g.spawn("ranger",(-18,-8));e.attack=0
        g.step(.02)
        self.assertGreater(e.telegraph,0);self.assertEqual(len(g.projectiles),0)
        for _ in range(35):g.step(.02)
        self.assertGreater(len(g.projectiles),0)

    def test_all_enemy_sizes_can_route_into_combat(self):
        for arena in range(3):
            for kind in ("ranger","heavy","flanker","boss"):
                with self.subTest(arena=arena,kind=kind):
                    g=Game();g.start_stage(arena+1);g.pending=1;g.spawn_timer=1000
                    g.hp=100000
                    e=g.spawn(kind,(0,19))
                    initial=g.hp
                    for _ in range(1500):g.step(.04)
                    self.assertLess(g.hp,initial)


if __name__=="__main__": unittest.main(verbosity=2)
