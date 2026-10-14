import subprocess
import unittest
from tests.test_graph import ROOT


class ControlTests(unittest.TestCase):
    def run_js(self,body):
        code="const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');const C=vm.runInNewContext(fs.readFileSync('web/controls.js','utf8')+'\\nPactControls');const c=new C({left:['ArrowLeft','KeyA'],jump:['Space'],action:['KeyX'],start:['Enter']});"+body
        result=subprocess.run(['node','-e',code],cwd=ROOT,capture_output=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_equivalent_keys_keep_action_held(self):
        self.run_js("c.keyDown('ArrowLeft');c.keyDown('KeyA');c.keyUp('ArrowLeft');assert.equal(c.consume().left,true);c.keyUp('KeyA');assert.equal(c.consume().left,false)")

    def test_touch_release_does_not_release_keyboard(self):
        self.run_js("c.keyDown('ArrowLeft');c.pointerDown(1,'left');c.pointerUp(1);assert.equal(c.consume().left,true)")

    def test_jump_is_an_edge_and_repeat_is_ignored(self):
        self.run_js("c.keyDown('Space');assert.equal(c.consume().jump,true);c.keyDown('Space');assert.equal(c.consume().jump,false);c.keyUp('Space');c.keyDown('Space');assert.equal(c.consume().jump,true)")

    def test_focus_loss_clears_every_input(self):
        self.run_js("c.keyDown('Space');c.pointerDown(2,'left');c.clear();assert.equal(c.consume().jump,false);assert.equal(c.consume().left,false)")
