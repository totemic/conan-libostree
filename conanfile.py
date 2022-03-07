#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Conan receipt package for USB Library
"""
import os
from conans import ConanFile, AutoToolsBuildEnvironment, RunEnvironment, tools


class LibOSTreeConan(ConanFile):
    """Download libostree source, build and create package
    """
    name = "libostree"
    version = "2022.1"
    settings = "os", "compiler", "build_type", "arch"
    topics = ("conan", "libostree", "ostree")
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {'shared': True, 'fPIC': True}
    homepage = "https://github.com/ostreedev/ostree"
    url = "http://github.com/totemic/conan-libostree"
    license = "LGPLv2+"
    description = "libostree is both a shared library and suite of command line tools that combines a git-like model for committing and downloading bootable filesystem trees, along with a layer for deploying them and managing the bootloader configuration"
    _source_subfolder = "source_subfolder"
    #exports = ["LICENSE.md"]

    def source(self):
        rev = "v" + self.version
        git = tools.Git(folder=self._source_subfolder)
        git.clone(self.homepage, rev, shallow=True)    
        #git.checkout(rev, submodule="shallow")
        with tools.chdir(self._source_subfolder):
            self.run("git submodule update --init")

    def requirements(self):
        self.requires("libglib2.0-0/2.56.4@totemic/stable")
        # if self.settings.os == "Linux":
            # todo: we should also add depdencies to libsystemd0.so.1, libcurl.so.4
            # right now this is handled by telling the linker to ignore unknown symbols in secondary dependencies
        #     self.requires("libcurl/7.66.0@totemic/stable")

    def build_requirements(self): 
        # installer = tools.SystemPackageTool()
        # installer = tools.SystemPackageTool(default_mode="disabled")
        # installer.install("libtool bison:amd64 libglib2.0-dev:arm64", update=True, force=True)
        # installer.install(["libtool", "bison:amd64", "libglib2.0-dev:arm64"], update=True)
        # installer.install(["libtool bison"], update=True)
        # installer.install(["libtool bison libglib2.0-dev liblzma-dev libmount-dev e2fslibs-dev libfuse-dev libcurl4-openssl-dev libsystemd-dev libgpgme-dev"], update=False, arch_names=)

        # tools.SystemPackageTool() doesn't support a mode where we install some native and some cross-compile libraries
        # for now, we'll directly execute apt, which will only work on debian systems
        if self.settings.os == "Linux":
            if tools.os_info.with_apt:
                self.run("sudo apt-get update")
                # build host dependencies
                self.run("sudo apt-get install -y --no-install-recommends libtool bison")
                # cross-compilation libraries
                packages = "libglib2.0-dev liblzma-dev libmount-dev e2fslibs-dev libfuse-dev libcurl4-openssl-dev libsystemd-dev libgpgme-dev".split(" ")
                parsed_packages = [self.get_package_name(pkg, str(self.settings.arch)) for pkg in packages]
                self.run("sudo apt-get install -y --no-install-recommends %s" % " ".join(parsed_packages))
                self.output.info("after build_requirements")
            else: 
                self.output.warn("Unsupported Linux version. Cannot install build dependencies, requires apt tooling.")

    def get_package_name(self, package, arch):
        arch_names = {"x86_64": "amd64",
                        "x86": "i386",
                        "ppc32": "powerpc",
                        "ppc64le": "ppc64el",
                        "armv7": "arm",
                        "armv7hf": "armhf",
                        "armv8": "arm64",
                        "s390x": "s390x"}
        if arch in arch_names:
            return "%s:%s" % (package, arch_names[arch])
        return package

    def build(self):
        if self.settings.os == "Linux":
            run_env = RunEnvironment(self)
            with tools.chdir(self._source_subfolder):
                with tools.environment_append(run_env.vars):
                    self.run("NOCONFIGURE=1 ./autogen.sh")
            #self.run("autoreconf --force --install --verbose", cwd=self._source_subfolder)
            static_compiler = os.environ['CC'] if 'CC' in os.environ else "gcc"
            cfgArgs = [
                "--with-curl", 
                "--without-soup", # --with-soup
                "--without-avahi",  # --with-avahi
                "--with-dracut",
                "--with-gpgme=no", 
                "--with-libmount",
                # --with-libarchive 
                # --with-grub2
            	# --with-grub2-mkconfig-path=/usr/sbin/grub-mkconfig
                "--with-selinux",
                "--with-libsystemd",
                "--with-systemdsystemunitdir=${libdir}/systemd/system",
                "--with-systemdsystemgeneratordir=${libdir}/systemd/system-generators", 
                "--with-static-compiler=%s" % static_compiler
            ]
            if self.options.shared:
                cfgArgs += ["--enable-shared", "--disable-static"]
            else:
                cfgArgs += ["--disable-shared", "--enable-static"]
            with tools.chdir(self._source_subfolder):
                autotools = AutoToolsBuildEnvironment(self)
                autotools.fpic = self.options.fPIC
                envVars = autotools.vars
                # set BASH_COMPLETIONSDIR to fixed value that honors ${prefix}. 
                # Otherwise it is set through pkgconfig variables and might fail in installation setp if it points to /usr/share 
                envVars["BASH_COMPLETIONSDIR"] = "${datadir}/bash-completion/completions"
                autotools.configure(args=cfgArgs, vars=envVars)
                autotools.make()
        else:
            # We allow using it on all platforms, but for anything except Linux nothing is produced
            # this allows unconditionally including this conan package on all platforms
            self.output.info("Nothing to be done for this OS")  

    def package(self):
        if self.settings.os == "Linux":
            with tools.chdir(self._source_subfolder):
                autotools = AutoToolsBuildEnvironment(self)
                autotools.install()
        else:
            # on non-linux platforms, expose the header files to help cross-development
            os.rename(self._source_subfolder+"/src/libostree/ostree-version.h.in", self._source_subfolder+"/src/libostree/ostree-version.h")
            self.copy(pattern="*.h", dst="include/ostree-1", src=self._source_subfolder+"/src/libostree", symlinks=True)

    def package_info(self):
        self.cpp_info.includedirs.append(os.path.join("include", "ostree-1"))
        if self.settings.os == "Linux":
            self.cpp_info.libs = ["ostree-1"]
