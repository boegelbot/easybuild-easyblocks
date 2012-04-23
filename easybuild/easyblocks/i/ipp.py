##
# Copyright 2009-2012 Stijn Deweirdt, Dries Verdegem, Kenneth Hoste, Pieter De Baets, Jens Timmerman
#
# This file is part of EasyBuild,
# originally created by the HPC team of the University of Ghent (http://ugent.be/hpc).
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

from easybuild.easyblocks.i.intelbase import IntelBase

class IPP(IntelBase):

    def sanitycheck(self):

        if not self.getcfg('sanityCheckPaths'):
            self.setcfg('sanityCheckPaths', {'files':["ipp/lib/intel64/libipp%s" % y for x in ["ac", "cc", "ch", "core", "cv", "dc", "di",
                                                                                            "i", "j", "m", "r", "s", "sc", "vc", "vm"]
                                                                                  for y in ["%s.a" % x, "%s.so" % x]],
                                            'dirs':["compiler/lib/intel64", "ipp/bin", "ipp/include",
                                                    "ipp/interfaces/data-compression", "ipp/tools/intel64"]
                                           })

            self.log.info("Customized sanity check paths: %s" % self.getcfg('sanityCheckPaths'))

        IntelBase.sanitycheck(self)