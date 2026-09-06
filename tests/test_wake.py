import unittest
from hermes_attention.wake import WakeController
class Fake:
 def __init__(self):self.calls=[]
 def start_listening(self,callback,**kw):self.calls.append('start');self.callback=callback
 def pause_listening(self,**kw):self.calls.append('pause')
 def resume_listening(self,**kw):self.calls.append('resume')
 def stop_listening(self,**kw):self.calls.append('stop')
class WakeTests(unittest.TestCase):
 def test_off_no_microphone_and_explicit_enable_only(self):
  engine=Fake();controller=WakeController(lambda _:None,module=engine,probe=lambda:{'available':True,'framework':'tflite'})
  self.assertEqual(controller.status()['state'],'off');self.assertEqual(engine.calls,[])
  with self.assertRaises(PermissionError):controller.start()
  controller.start(authorized=True);controller.start(authorized=True);self.assertEqual(engine.calls,['start'])
  controller.stop();controller.stop();self.assertEqual(engine.calls,['start','stop'])
 def test_one_wake_pauses_no_duplicate_until_resume(self):
  engine=Fake();events=[];controller=WakeController(events.append,module=engine,probe=lambda:{'available':True,'framework':'tflite'})
  controller.start(authorized=True);engine.callback();engine.callback();self.assertEqual(len(events),1)
  controller.resume();engine.callback();self.assertEqual(len(events),2);self.assertNotEqual(events[0]['eventId'],events[1]['eventId'])
 def test_detector_failure_propagates_while_controller_and_worker_stay_alive(self):
  engine=Fake();engine.on_failure=lambda detector:engine.calls.append('released-failed-owner')
  def start(callback,**kw):engine.callback=callback;return engine
  engine.start_listening=start;events=[];controller=WakeController(events.append,module=engine,probe=lambda:{'available':True,'framework':'tflite'})
  started=controller.start(authorized=True);engine.on_failure(engine)
  self.assertEqual(controller.status()['state'],'off');self.assertEqual(events[-1]['event'],'wake.state')
  self.assertGreater(events[-1]['result']['revision'],started['revision']);self.assertIn('released-failed-owner',engine.calls)
  self.assertTrue(controller.status()['available'])
 def test_missing_dependencies_do_not_start_or_install(self):
  engine=Fake();controller=WakeController(lambda _:None,module=engine,probe=lambda:{'available':False,'missing':['dependency']})
  self.assertEqual(controller.start(authorized=True)['state'],'unavailable');self.assertEqual(engine.calls,[])
