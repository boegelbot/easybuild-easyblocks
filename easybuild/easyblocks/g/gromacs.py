##
# Copyright 2013 Ghent University
#
# This file is part of EasyBuild,
# originally created by the HPC team of Ghent University (http://ugent.be/hpc/en),
# with support of Ghent University (http://ugent.be/hpc),
# the Flemish Supercomputer Centre (VSC) (https://vscentrum.be/nl/en),
# the Hercules foundation (http://www.herculesstichting.be/in_English)
# and the Department of Economy, Science and Innovation (EWI) (http://www.ewi-vlaanderen.be/en).
#
# http://github.com/hpcugent/easybuild
#
# EasyBuild is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation v2.
#
# EasyBuild is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with EasyBuild.  If not, see <http://www.gnu.org/licenses/>.
##
"""
EasyBuild support for building and installing GROMACS, implemented as an easyblock

@author: Kenneth Hoste (Ghent University)
"""
import os
import re
from distutils.version import LooseVersion
from vsc.utils.missing import any

import easybuild.tools.environment as env
from easybuild.easyblocks.generic.configuremake import ConfigureMake
from easybuild.easyblocks.generic.cmakemake import CMakeMake
from easybuild.framework.easyconfig import CUSTOM
from easybuild.tools.modules import get_software_root

class EB_GROMACS(CMakeMake):
    """Support for building/installing GROMACS."""

    @staticmethod
    def extra_options():
        extra_vars = {
            'mpisuffix': ['_mpi', "Suffix to append to MPI-enabled executables", CUSTOM],
        }
        return ConfigureMake.extra_options(extra_vars)

    def configure_step(self):
        """Custom configuration procedure for GROMACS: set configure options for configure or cmake."""

        if LooseVersion(self.version) < LooseVersion('4.6'):

            # Use static libraries if possible
            self.cfg.update('configopts', "--enable-static")

            # Use external BLAS and LAPACK
            self.cfg.update('configopts', "--with-external-blas --with-external-lapack")

            # Don't use the X window system
            self.cfg.update('configopts', "--without-x")

            if self.toolchain.options.get('usempi', None):
                self.cfg.update('configopts', "--enable-mpi --program-suffix={0}".format(self.cfg['mpisuffix']))

            # OpenMP is not supported for versions older than 4.5.
            if LooseVersion(self.version) >= LooseVersion('4.5'):
                # enable OpenMP support if desired
                if self.toolchain.options.get('openmp', None):
                    self.cfg.update('configopts', "--enable-threads")
                else:
                    self.cfg.update('configopts', "--disable-threads")
            elif self.toolchain.options.get('openmp', None):
                self.log.error("GROMACS version {0} does not support OpenMP.".format(LooseVersion(self.version)))

            # GSL support
            if get_software_root('GSL'):
                self.cfg.update('configopts', "--with-gsl")
            else:
                self.cfg.update('configopts', "--without-gsl")

            # I don't think it's necessary to explicitly set the location
            # of math libraries (MKL and/or BLAS, LAPACK) but we shall see.
            
            # Because ConfigureMake is (currently) an ancestral class of
            # CMakeMake, we may not need to specify it as an ancestral class
            # of gromacs.py.
            ConfigureMake.configure_step(self)
        else:
            # build a release build
            self.cfg.update('configopts', "-DCMAKE_BUILD_TYPE=Release")

            # prefer static libraries, if available
            self.cfg.update('configopts', "-DGMX_PREFER_STATIC_LIBS=ON")

            # always specify to use external BLAS/LAPACK
            self.cfg.update('configopts', "-DGMX_EXTERNAL_BLAS=ON -DGMX_EXTERNAL_LAPACK=ON")

            # disable GUI tools
            self.cfg.update('configopts', "-DGMX_X11=OFF")

            # enable OpenMP support if desired
            if self.toolchain.options.get('openmp', None):
                self.cfg.update('configopts', "-DGMX_OPENMP=ON")
            else:
                self.cfg.update('configopts', "-DGMX_OPENMP=OFF")

            # enable MPI support if desired
            if self.toolchain.options.get('usempi', None):
                self.cfg.update('configopts', "-DGMX_MPI=ON -DGMX_THREAD_MPI=OFF")
            else:
                self.cfg.update('configopts', "-DGMX_MPI=OFF")

            # explicitly disable GPU support if CUDA is not available,
            # to avoid that GROMACS find and uses a system-wide CUDA compiler
            cuda = get_software_root('CUDA')
            if cuda:
                self.cfg.update('configopts', "-DGMX_GPU=ON -DCUDA_TOOLKIT_ROOT_DIR=%s" % cuda)
            else:
                self.cfg.update('configopts', "-DGMX_GPU=OFF")

            if get_software_root('imkl'):
                # using MKL for FFT, so it will also be used for BLAS/LAPACK
                self.cfg.update('configopts', '-DGMX_FFT_LIBRARY=mkl -DMKL_INCLUDE_DIR="$EBROOTMKL/mkl/include" ')
                mkl_libs = [os.path.join(os.getenv('LAPACK_LIB_DIR'), lib) for lib in ['libmkl_lapack.a']]
                self.cfg.update('configopts', '-DMKL_LIBRARIES="%s" ' % ';'.join(mkl_libs))
            else:
                for libname in ['BLAS', 'LAPACK']:
                    lib_dir = os.getenv('%s_LIB_DIR' % libname)
                    libs = os.getenv('LIB%s' % libname)
                    self.cfg.update('configopts', '-DGMX_%s_USER="-L%s %s"' % (libname, lib_dir, libs))

            # enable GSL when it's provided
            if get_software_root('GSL'):
                self.cfg.update('configopts', "-DGMX_GSL=ON")
            else:
                self.cfg.update('configopts', "-DGMX_GSL=OFF")

            # set regression test path
            prefix = 'regressiontests'
            if any([src['name'].startswith(prefix) for src in self.src]):
                self.cfg.update('configopts', "-DREGRESSIONTEST_PATH='%%(builddir)s/%s-%%(version)s' " % prefix)

            # complete configuration with configure_method of parent
            out = super(EB_GROMACS, self).configure_step()

            # for recent GROMACS versions, make very sure that a decent BLAS, LAPACK and FFT is found and used
            if LooseVersion(self.version) >= LooseVersion('4.6.5'):
                patterns = [
                    r"Using external FFT library - \S*",
                    r"Looking for dgemm_ - found",
                    r"Looking for cheev_ - found",
                ]
                for pattern in patterns:
                    regex = re.compile(pattern, re.M)
                    if not regex.search(out):
                        self.log.error("Pattern '%s' not found in GROMACS configuration output." % pattern)

    def build_step(self):
        """ For older versions of GROMACS, allow for a separate mdrun build if
            MPI support has been requested. """
        if LooseVersion(self.version) < LooseVersion('4.6'):
            self.cfg.update("prebuildopts", 'LIBS="${EBVARLIBLAPACK} ${LIBS}"')
            if "--enable-mpi" in self.cfg['configopts']:
                self.cfg.update("buildopts", "mdrun")
        super(EB_GROMACS, self).build_step()

    def install_step(self):
        """ For older versions of GROMACS, allow for a separate mdrun install
            if MPI support has been requested. """
        if LooseVersion(self.version) < LooseVersion('4.6'):
            if "--enable-mpi" in self.cfg['configopts']:
                self.cfg.update("installopts", "install-mdrun")
        super(EB_GROMACS, self).install_step()

    def test_step(self):
        """Specify to running tests is done using 'make check'."""
        # allow to escape testing by setting runtest to False
        if not self.cfg['runtest'] and not isinstance(self.cfg['runtest'], bool):
            self.cfg['runtest'] = 'check'
            if LooseVersion(self.version) < LooseVersion('4.6'):
                self.cfg['runtest'] = 'LIBS="${EBVARLIBLAPACK} ${LIBS}" check'

        # make very sure OMP_NUM_THREADS is set to 1, to avoid hanging GROMACS regression test
        env.setvar('OMP_NUM_THREADS', '1')

        super(EB_GROMACS, self).test_step()

    def sanity_check_step(self):
        """Custom sanity check for GROMACS."""

        suff = ''
        if self.toolchain.options.get('usempi', None):
            suff = self.cfg['mpisuffix']

        # check for a handful of binaries/libraries that should be there
        libnames = ['gromacs']
        if LooseVersion(self.version) < LooseVersion('5.0'):
            libnames = ['gmxana', 'gmx', 'md']
            # I don't know when the gmxpreprocess library was introduced.
            # This LooseVersion number may have to be tweaked.
            if LooseVersion(self.version) > LooseVersion('3.3.3'):
                libnames.append('gmxpreprocess')
        libs = ['lib%s%s.a' % (libname, suff) for libname in libnames]
        dirs = ['include/gromacs']
        # I don't know when the pkgconfig directory was introduced.
        # This LooseVersion number may have to be tweaked.
        if LooseVersion(self.version) > LooseVersion('3.3.3'):
            dirs.append(('lib/pkgconfig', 'lib64/pkgconfig'))
        custom_paths = {
            'files': ['bin/%s%s' % (binary, suff) for binary in ['editconf', 'g_lie', 'genbox', 'genconf', 'mdrun']] +
                     [(os.path.join('lib', lib), os.path.join('lib64', lib)) for lib in libs],
            'dirs': dirs,
        }
        super(EB_GROMACS, self).sanity_check_step(custom_paths=custom_paths)
