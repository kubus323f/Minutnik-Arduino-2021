import importlib
import os
import runpy
import sys

# MPFB2 is installed and enabled as a Blender Extension by the workflow.
# Locate its real extension namespace and provide the legacy `mpfb` alias expected
# by the validation script, without registering the extension a second time.
prefix = None
for name in list(sys.modules):
    if name.endswith('.mpfb') and name.startswith('bl_ext.'):
        prefix = name
        break

if prefix is None:
    prefix = 'bl_ext.ci_local.mpfb'
    mpfb_mod = importlib.import_module(prefix)
    if getattr(mpfb_mod, 'MPFB_CONTEXTUAL_INFORMATION', None) is None:
        mpfb_mod.register()
else:
    mpfb_mod = importlib.import_module(prefix)

# Mirror already-loaded extension modules into the alias namespace.
for name, module in list(sys.modules.items()):
    if name == prefix or name.startswith(prefix + '.'):
        alias = 'mpfb' + name[len(prefix):]
        sys.modules.setdefault(alias, module)

# Prevent the old validation script from double-registering MPFB.
mpfb_mod.register = lambda: None
sys.modules['mpfb'] = mpfb_mod

script = os.path.join(os.getcwd(), 'ci', 'build_frieren.py')
runpy.run_path(script, run_name='__main__')
