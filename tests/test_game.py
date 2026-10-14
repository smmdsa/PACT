import json
import unittest
from pact.reference import Machine
from tests.test_module_execution import execute
from tools.make_game import game_document


class GameTests(unittest.TestCase):
    def setUp(self):
        self.doc=game_document()
        self.assertIsInstance(self.doc,dict)
        self.vm=Machine(self.doc)
        self.vm.call('game.init')
        self.vm.state['input.start'][0]=1
        self.vm.call('game.tick')
        self.vm.state['input.start'][0]=0

    def field(self,key,value=None,index=0):
        if value is not None:self.vm.state[key][index]=value
        return self.vm.state[key][index]

    def test_start_and_horizontal_motion(self):
        self.assertEqual(self.field('game.phase'),1)
        start=self.field('player.x')
        self.field('input.right',1)
        for _ in range(10):self.vm.call('game.tick')
        self.assertGreater(self.field('player.x'),start)

    def test_jump_requires_ground_or_coyote(self):
        self.field('player.grounded',1);self.field('input.jump',1)
        self.vm.call('player.move')
        self.assertLess(self.field('player.vy'),0)
        self.field('player.coyote',0);self.field('player.grounded',0);self.field('player.vy',0)
        self.vm.call('player.move')
        self.assertGreaterEqual(self.field('player.vy'),0)

    def test_floor_prevents_falling(self):
        self.field('player.x',48*256);self.field('player.y',210*256)
        self.field('player.vy',2048)
        for _ in range(20):self.vm.call('player.move')
        self.assertEqual(self.field('player.y'),210*256)
        self.assertEqual(self.field('player.grounded'),1)

    def test_ladder_crosses_the_platform_opening(self):
        self.field('player.x',306*256);self.field('player.y',210*256);self.field('input.up',1)
        for _ in range(32):self.vm.call('player.move')
        self.assertLess(self.field('player.y'),176*256)

    def test_damage_has_invulnerability(self):
        self.vm.call('player.damage')
        lives=self.field('player.lives')
        self.vm.call('player.damage')
        self.assertEqual(self.field('player.lives'),lives)
        self.assertGreater(self.field('player.invulnerable'),0)

    def test_pickup_and_throw_preserve_single_owner(self):
        self.field('player.x',self.field('item.x',index=0));self.field('player.y',210*256)
        self.field('input.action',1)
        self.vm.call('items.interact')
        self.assertEqual(self.field('player.carried'),0)
        self.assertEqual(self.field('item.mode',index=0),1)
        self.vm.call('items.interact')
        self.assertEqual(self.field('player.carried'),-1)
        self.assertEqual(self.field('item.mode',index=0),2)
        self.assertNotEqual(self.field('item.vx',index=0),0)

    def test_checkpoint_and_fall_respawn(self):
        self.field('player.x',1300*256)
        self.vm.call('world.progress')
        self.assertEqual(self.field('game.checkpoint'),1)
        self.field('player.y',400*256)
        self.vm.call('world.progress')
        self.assertEqual(self.field('player.x'),self.field('checkpoint.x'))
        self.assertEqual(self.field('player.lives'),2)

    def test_win_and_restart(self):
        self.field('enemy.alive',0,index=5);self.field('game.gems',3)
        self.field('player.x',2760*256)
        self.vm.call('world.progress')
        self.assertEqual(self.field('game.phase'),2)
        self.field('input.start',1);self.vm.call('game.tick')
        self.assertEqual(self.field('game.phase'),1)
        self.assertEqual(self.field('player.lives'),3)
        self.assertEqual(self.field('game.gems'),0)

    def test_wasm_matches_reference_for_input_sequence(self):
        calls=[{'fn':'game.init'}, {'set':{'input.start':[1]},'fn':'game.tick'}, {'set':{'input.start':[0],'input.right':[1]},'fn':'game.tick'}]
        for _ in range(30):calls.append({'fn':'game.tick'})
        for call in calls:
            for key,values in call.get('set',{}).items():self.vm.state[key]=list(values)
            self.vm.call(call['fn'])
        actual,_=execute(self.doc,calls)
        self.assertEqual(actual.returncode,0,actual.stderr)
        self.assertEqual(json.loads(actual.stdout)['state'],self.vm.state)


if __name__=='__main__':unittest.main()
