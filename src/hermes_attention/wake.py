"""Optional maintained Hermes wake detector, with no dependency installation/network.

The helper owns only its listener. Startup is off, EOF releases microphone, and a
wake pauses detection until the native owner explicitly resumes after voice capture.
"""
import importlib.util
import platform
from pathlib import Path
from uuid import uuid4

class WakeController:
    def __init__(self,emit,*,module=None,probe=None):
        self.emit=emit;self.module=module;self.probe=probe or self.capability;self.owner=object();self.state='off';self.generation=None;self.revision=0

    @staticmethod
    def capability():
        missing=[]
        for name in ('sounddevice','numpy','openwakeword'):
            if importlib.util.find_spec(name) is None:missing.append(name)
        framework='tflite' if platform.system()=='Darwin' and platform.machine()=='arm64' else 'onnx'
        if framework=='tflite' and not any(importlib.util.find_spec(name) for name in ('tflite_runtime','ai_edge_litert')):missing.append('macOS TFLite runtime')
        root=Path.home()/'.hermes/hermes-agent'
        model=root/'tools/wakewords'/('hey_hermes.'+framework)
        if not model.is_file():missing.append('bundled Hey Hermes wake model')
        spec=importlib.util.find_spec('openwakeword')
        if spec and spec.submodule_search_locations:
            models=Path(next(iter(spec.submodule_search_locations)))/'resources/models'
            for name in ('embedding_model','melspectrogram'):
                if not (models/(name+'.'+framework)).is_file():missing.append(name+' model')
        return {'available':not missing,'missing':missing,'phrase':'Hey Hermes','framework':framework,'state':'off','microphone_checked':False,'hint':'Optional detection uses the installed Hermes phrase. Talk remains available; missing dependencies/models are not installed automatically.'}

    def status(self):
        if self.module and self.state in {'listening','paused'} and hasattr(self.module,'owns_listener') and not self.module.owns_listener(self.owner):self.state='off';self.generation=None
        value={**self.probe(),'state':self.state,'generation':self.generation,'revision':self.revision}
        if self.module and self.state=='listening' and hasattr(self.module,'audio_is_silent') and self.module.audio_is_silent():value['hint']='Microphone stream is silent; check backend microphone permission. Wake detection is not verified.'
        return value

    def start(self,*,authorized=False):
        if not authorized:raise PermissionError('Enable wake explicitly in the local owner interface')
        if self.state!='off':return self.status()
        available=self.probe()
        if not available['available']:return {**available,'state':'unavailable'}
        if self.module is None:
            from tools import wake_word,lazy_deps
            import openwakeword.utils
            # Process-local guards prevent maintained engine convenience auto-installs/downloads.
            def installed_only(feature,*args,**kwargs):
                if not lazy_deps.is_available(feature):raise RuntimeError('Optional wake dependency unavailable; no installation attempted')
                return True
            lazy_deps.ensure=installed_only
            openwakeword.utils.download_models=lambda *args,**kwargs: None
            self.module=wake_word
        self.generation=str(uuid4());self.state='starting'
        try:
            detector=self.module.start_listening(self._wake,owner=self.owner,config={'enabled':True,'provider':'openwakeword','phrase':'hey hermes','openwakeword':{'model':'hey_hermes','inference_framework':available['framework']},'start_new_session':False})
            self.state='listening';self.revision+=1
            if detector is not None and hasattr(detector,'on_failure'):
                original=detector.on_failure;generation=self.generation
                def failed(value):
                    try:
                        if original:original(value)
                    finally:
                        if self.generation==generation:
                            self.state='off';self.generation=None;self.revision+=1
                            self.emit({'event':'wake.state','result':{**self.status(),'hint':'Wake detector stopped unexpectedly; enable again only after checking microphone status.'}})
                detector.on_failure=failed
        except Exception:
            self.module.stop_listening(owner=self.owner);self.state='off';self.generation=None;raise
        return self.status()

    def _wake(self):
        if self.state!='listening':return
        self.state='paused';self.revision+=1;self.module.pause_listening(owner=self.owner)
        self.emit({'event':'wake.detected','eventId':str(uuid4()),'generation':self.generation,'phrase':'Hey Hermes','revision':self.revision})

    def pause(self):
        if self.state=='listening':self.module.pause_listening(owner=self.owner);self.state='paused';self.revision+=1
        return self.status()

    def resume(self):
        if self.state=='paused':self.module.resume_listening(owner=self.owner);self.state='listening';self.revision+=1
        return self.status()

    def stop(self):
        if self.module and self.state!='off':self.module.stop_listening(owner=self.owner)
        self.state='off';self.generation=None;self.revision+=1;return self.status()
