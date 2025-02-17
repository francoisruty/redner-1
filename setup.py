# Adapted from https://github.com/pybind/cmake_example/blob/master/setup.py
import os
import re
import sys
import platform
import subprocess
import importlib
from sysconfig import get_paths

from setuptools import setup, Extension
from setuptools.command.build_ext import build_ext
from setuptools.command.install import install
from distutils.sysconfig import get_config_var
from distutils.version import LooseVersion

class RemoveOldRednerBeforeInstall(install):
    def run(self):
        # Remove old redner packages installed by distutils
        from distutils import sysconfig as sc
        site_packages_dir = sc.get_python_lib()
        import shutil
        import glob
        egg_info_path = glob.glob(os.path.join(site_packages_dir, 'redner-0.0.1-*.egg-info'))
        for p in egg_info_path:
            try:
                os.remove(p)
            except:
                print('Warning: detect old redner installation file {} and could not remove it. You may want to remove the file manually.'.format(p))

        install.run(self)

class CMakeExtension(Extension):
    def __init__(self, name, sourcedir, build_with_cuda):
        Extension.__init__(self, name, sources=[])
        self.sourcedir = os.path.abspath(sourcedir)
        self.build_with_cuda = build_with_cuda

class CopyExtension(Extension):
    def __init__(self, name, filename_list):
        Extension.__init__(self, name, sources=[])
        self.filename_list = filename_list

class Build(build_ext):
    def run(self):
        try:
            out = subprocess.check_output(['cmake', '--version'])
        except OSError:
            raise RuntimeError("CMake must be installed to build the following extensions: " +
                               ", ".join(e.name for e in self.extensions))

        super().run()

    def build_extension(self, ext):
        if isinstance(ext, CMakeExtension):
            extdir = os.path.abspath(os.path.dirname(self.get_ext_fullpath(ext.name)))
            info = get_paths()
            include_path = info['include']
            cmake_args = ['-DCMAKE_LIBRARY_OUTPUT_DIRECTORY=' + extdir,
                          '-DPYTHON_INCLUDE_PATH=' + include_path]

            cfg = 'Debug' if self.debug else 'Release'
            build_args = ['--config', cfg]

            if platform.system() == "Windows":
                cmake_args += ['-DCMAKE_LIBRARY_OUTPUT_DIRECTORY_{}={}'.format(cfg.upper(), extdir)]
                if sys.maxsize > 2**32:
                    cmake_args += ['-A', 'x64']
                build_args += ['--', '/m']
            else:
                cmake_args += ['-DCMAKE_BUILD_TYPE=' + cfg]
                build_args += ['--', '-j8']

            if ext.build_with_cuda:
                cmake_args += ['-DREDNER_CUDA=1']

            env = os.environ.copy()
            env['CXXFLAGS'] = '{} -DVERSION_INFO=\\"{}\\"'.format(env.get('CXXFLAGS', ''),
                                                                  self.distribution.get_version())
            if not os.path.exists(self.build_temp):
                os.makedirs(self.build_temp)
            subprocess.check_call(['cmake', ext.sourcedir] + cmake_args, cwd=self.build_temp, env=env)
            subprocess.check_call(['cmake', '--build', '.'] + build_args, cwd=self.build_temp)
        elif isinstance(ext, CopyExtension):
            extdir = os.path.abspath(os.path.dirname(self.get_ext_fullpath(ext.name)))
            # Copy the files to extdir
            from shutil import copy
            for f in ext.filename_list:
                print('Copying {} to {}'.format(f, extdir))
                copy(f, extdir)
        else:
            super().build_extension(ext)

torch_spec = importlib.util.find_spec("torch")
tf_spec = importlib.util.find_spec("tensorflow")
packages = []
build_with_cuda = False
if torch_spec is not None:
    packages.append('pyredner')
    import torch
    if torch.cuda.is_available():
        build_with_cuda = True
if tf_spec is not None:
    packages.append('pyredner_tensorflow')
    if not build_with_cuda:
        import tensorflow as tf
        if tf.test.is_gpu_available(cuda_only=True, min_cuda_compute_capability=None):
            build_with_cuda = True
if len(packages) == 0:
    print('Error: PyTorch or Tensorflow must be installed.')
    exit()
# Override build_with_cuda with environment variable
if 'REDNER_CUDA' in os.environ:
    build_with_cuda = os.environ['REDNER_CUDA'] == '1'

# OpenEXR Python installation
openexr_python_version = "1.3.2"
openexr_python_compiler_args = ['-g', '-DVERSION="%s"' % openexr_python_version]
if sys.platform == 'darwin':
    openexr_python_compiler_args.append('-std=c++14')
    if 'MACOSX_DEPLOYMENT_TARGET' not in os.environ:
        current_system = LooseVersion(platform.mac_ver()[0])
        python_target = LooseVersion(
            get_config_var('MACOSX_DEPLOYMENT_TARGET'))
        if python_target < '10.9' and current_system >= '10.9':
            os.environ['MACOSX_DEPLOYMENT_TARGET'] = '10.9'
openexr_include_dir = 'redner-dependencies/openexr/include/OpenEXR'
openexr_lib_dir = ''
if sys.platform == 'darwin':
    openexr_lib_dir = 'redner-dependencies/openexr/lib-macos'
elif sys.platform == 'linux':
    openexr_lib_dir = 'redner-dependencies/openexr/lib-linux'
openexr_link_args = [os.path.join(openexr_lib_dir, 'libIex-2_3_s.a'),
                     os.path.join(openexr_lib_dir, 'libHalf-2_3_s.a'),
                     os.path.join(openexr_lib_dir, 'libImath-2_3_s.a'),
                     os.path.join(openexr_lib_dir, 'libIlmImf-2_3_s.a')]
openexr_libraries = []
if sys.platform == 'darwin':
    # OS X has zlib by default, link to it.
    openexr_libraries = ['z']
    # Supress warning by setting to the host's OS X version
    osx_ver = platform.mac_ver()[0]
    osx_ver = '.'.join(osx_ver.split('.')[:2])
    openexr_python_compiler_args.append('-mmacosx-version-min=' + osx_ver)
    openexr_link_args.append('-mmacosx-version-min=' + osx_ver)

dynamic_libraries = []
# Make Embree and OptiX part of the package
if sys.platform == 'darwin':
    dynamic_libraries.append('redner-dependencies/embree/lib-macos/libembree3.dylib')
    dynamic_libraries.append('redner-dependencies/embree/lib-macos/libtbb.dylib')
    dynamic_libraries.append('redner-dependencies/embree/lib-macos/libtbbmalloc.dylib')
elif sys.platform == 'linux':
    dynamic_libraries.append('redner-dependencies/embree/lib-linux/libembree3.so.3')
    dynamic_libraries.append('redner-dependencies/embree/lib-linux/libtbb.so.2')
    dynamic_libraries.append('redner-dependencies/embree/lib-linux/libtbbmalloc.so.2')
    dynamic_libraries.append('redner-dependencies/optix/lib64/liboptix_prime.so.6.5.0')

setup(name = 'redner',
      version = '0.0.2',
      description = 'A differentiable Monte Carlo ray tracer.',
      author = 'Tzu-Mao Li',
      license = 'MIT',
      packages = packages,
      ext_modules = [CMakeExtension('redner', '', build_with_cuda),
                     Extension('OpenEXR',
                        ['openexrpython/OpenEXR.cpp'],
                        include_dirs=[openexr_include_dir],
                        library_dirs=[openexr_lib_dir, '/usr/lib', '/usr/local/lib', '/opt/local/lib'],
                        libraries=openexr_libraries,
                        extra_compile_args=openexr_python_compiler_args,
                        extra_link_args=openexr_link_args),
                     CopyExtension('redner-dependencies', dynamic_libraries),
                     CopyExtension('openexrpython', ['openexrpython/Imath.py'])],
      cmdclass = dict(build_ext=Build, install=RemoveOldRednerBeforeInstall),
      install_requires = ['scikit-image'],
      zip_safe = False)

