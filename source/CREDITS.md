# Credits and component notices

Neon Breach was created for this project. Game source, procedural arena and robot
geometry, weapon models, effects, and synthesized WAV audio are original project
content. No third-party character, model, texture, music or commercial asset pack
is used.

The project code is provided for the user's use and modification. Third-party
components retain their respective copyrights and licenses; this document does
not change them.

| Component | Use | License / source |
|---|---|---|
| Python 3.12.14 | Bundled interpreter and standard library | PSF and bundled notices, `licenses/Python.txt`; https://www.python.org/ |
| Panda3D 1.10.16 | 3D rendering, window, UI and audio | Modified BSD, `licenses/Panda3D.txt`; https://github.com/panda3d/panda3d/tree/v1.10.16 |
| PyInstaller 6.22.0 | Windows bootloader and packaging | GPL with distribution exception, `licenses/PyInstaller.txt`; https://pyinstaller.org/ |
| Rajdhani Medium | Interface font | SIL Open Font License 1.1, `licenses/Rajdhani-OFL.txt`; https://github.com/google/fonts/tree/main/ofl/rajdhani |

The prebuilt Panda3D runtime also incorporates or links native components such as
FreeType, zlib, libpng, libjpeg, libtiff, OpenEXR, Eigen and OpenSSL. The selected
audio plugin uses OpenAL Soft and may include Ogg/Vorbis decoding. Windows builds
also link the unmodified NVIDIA Cg runtime and Microsoft runtime DLLs even though
the game does not use Cg shaders. Corresponding notices are in `licenses`.
The dependency list and upstream source locations are documented at:

https://docs.panda3d.org/1.10/python/distribution/thirdparty-licenses

This software is based in part on the work of the Independent JPEG Group.
Portions of this software are copyright The FreeType Project (www.freetype.org).
This product includes software developed by the OpenSSL Project for use in the
OpenSSL Toolkit. This product includes cryptographic software written by Eric
Young (eay@cryptsoft.com). This product includes software written by Tim Hudson
(tjh@cryptsoft.com).

OpenAL Soft is licensed under LGPL. Its source is available from
https://github.com/kcat/openal-soft and Panda3D's audio integration source is at
https://github.com/panda3d/panda3d/tree/v1.10.16/panda/src/openalAudio . The engine's
third-party build scripts are at https://github.com/rdb/panda3d-thirdparty .
The separately supplied engine/audio DLLs can be replaced by compatible rebuilt
versions. Review the upstream version and build configuration if redistributing
modified third-party binaries.

`licenses/SOURCES.txt` records the upstream locations of the included notices.
The bundled font and all audio files are local. These links are documentation;
the executable does not open or fetch them.
