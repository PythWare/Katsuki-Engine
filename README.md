# Version 1.0

Katsuki Engine 1.0 has released. It has a new GUI, a different theme for the Mod Manager, and new subcontainer logic. My work on Aldnoah Engine has taught me a lot about Omega Force's signatureless subcontainers, so the new KE will has major improvements for subcontainer handling so it matches my Aldnoah Engine.

KE 1.0 also unpacks files with proper filenames and reconstruct paths when feasible.

# Katsuki Engine

Katsuki Engine is a GUI toolkit for modding Attack On Titan 2, KE is the foundation of the modding ecosytem for Attack On Titan games. KE can unpack all of the BIN containers, comes with a Mod Creator that turns modded files into AOT2M/AOT2MI mod files (custom mod package/mod installer formats I designed to be used with Katsuki Mod Manager), and a Mod Manager for applying/disabling mods as well as truncating containers back to their original sizes and reverting to original unmoddified versions when disabling all mods.

# What's needed to use

1. Python 3 and Pillow (a Python imaging library). To install pillow open an admin command prompt and enter `python -m pip install pillow`

2. Place the downloaded files (main.pyw, filename.ref, and the Katsuki_Logic folder) in the game's directory (i.e., C:\Program Files (x86)\Steam\steamapps\common\AoT2\LINKDATA)

If you have python 3 and pillow installed you should be able to run Katsuki Engine by double clicking main.pyw. If it doesn't work open cmd in the directory and type `python main.pyw'

Don't remove taildata, taildata section will explain this

Make sure to read KE_Guide.txt if you intend to mod AOT2.

# Main GUI

KE will unpack the BIN containers, unpack subcontainers, decompress, etc. unpacked files will have their original filenames and only default to incremented filenames if the executables lack a filename for said files.

When unpacking don't assume KE is frozen/stuck if the unpack bar doesn't progress, it isn't. It just takes several minutes to fully unpack/decompress because it's a lot of data being read and a lot of files being unpacked. The speed of unpacking may be affected by if you're unpacking in a HDD or SSD.

<img width="1050" height="972" alt="nk6" src="https://github.com/user-attachments/assets/7762e9c3-a746-45f4-aa87-160a003129bb" />

# Mod Creator

The Mod Creator turns modded files into aot2m/aot2mi files and allows you to enter metadata like author of the mod, version of mod, description, preview images to be used with the mod to be displayed in the mod manager, selecting modded files to pack into the package, music with your mod release, etc. To briefly explain the Mod Creator, it turns modded files into 1 of 2 things. a mod package (aot2m) which the bulk of future mods will be or a mod installer (aot2mi). Mod packages will be aot2m files while mod installers will be aot2mi files. Mod installers will be used when you release a mod that is single or multi-choice. suppose you want to release a texture mod (you're not limited to texture mods, this is just an example) that upscales a texture, let's say you wanted to give the user the option to select a low, mid, or high resolution version. You'd make it a mod installer release so that the user can choose which version to use. If all you want to do is create a mod that doesn't need options like a translation mod as an example, you'd release the mod as a mod package rather than mod installer.

Other features are Mod Genre tagging added as toggles (All, Texture, Audio, Model, Overhaul as the genres) for Standard Payload and Installer Architect, Build Mod toggles (debug or release versions) added to both as well. I also implemented a custom zlib compression algorithm for text descriptions for mods since some users may type long descriptions. Debug mods have a 5k character limit for descriptions while release Mods will use compression. If a mod is toggled as a release Katsuki will attempt to compress the description with zlib and use KRLE (Katsuki RLE, a custom mini RLE compression algorithm I implemented) on padded data (any unused space leftover if the description doesn't use the full 5k character limit). If the output is smaller then when the mod file is created it'll write the compressed text or if it's larger it'll write the original text and perform KRLE on padded data. So basically, ZLIB and KRLE is used on release tagged mods or just KRLE if ZLIB doesn't actually make the text smaller. 

<img width="1919" height="1020" alt="nk8" src="https://github.com/user-attachments/assets/698b34f0-a421-456e-a8a9-a08a23ed83de" />

<img width="1920" height="1017" alt="nk9" src="https://github.com/user-attachments/assets/0533e15b-47bb-41ee-a89c-435c82517d10" />

<img width="1920" height="1027" alt="nk10" src="https://github.com/user-attachments/assets/66a35eb3-f8bd-4619-a800-107a72dd2f89" />

# Mod Manager, the Blast Chamber

KE Mod Manager supports safely applying/disabling mods (aot2m/aot2mi files) as well as resetting the container files with the disable all mods button (truncates containers to original sizes and reverts to fresh unmodded versions), displaying the metadata of mods created, displays preview images of mods, plays music that is included in a mod file, tracks mods currently applied, disable playing music (incase you prefer silence), filter mods by typing or selecting the mod genre toggles, etc. aot2mi files are as explained earlier, mod installers so when you want to install such mods the Katsuki Installer Wizard will appear with the options, descriptions, images, etc of the mod installer.

To navigate the Katsuki Mod Manager use left click dragging or if you want to get to an exact mod just type the mod's name in the search bar. you zan zoom in/out with mousewheel.

<img width="1916" height="1032" alt="nk15" src="https://github.com/user-attachments/assets/37aea110-d8a3-489a-85f5-35946e04079b" />

<img width="1907" height="1033" alt="nk16" src="https://github.com/user-attachments/assets/185f77cd-3f1c-49bd-a516-cf6def421123" />

# Katsuki Installer Wizard

The Installer Wizard will popup when applying AOT2MI mods, mod installer releases. It essentially allows the user to choose what to install from the mod as explained in Mod Creator section.

<img width="906" height="725" alt="nk17" src="https://github.com/user-attachments/assets/9d40b0bc-e234-440e-bf79-efb6adbbab95" />

<img width="899" height="742" alt="nk18" src="https://github.com/user-attachments/assets/9a4479f6-6761-425f-9bba-2eddc74017b6" />

<img width="897" height="744" alt="nk19" src="https://github.com/user-attachments/assets/32958a1c-c8a0-4a32-b0d8-46411faadba5" />

# How the Mod Manager applies/disables mods

Katsuki Engine doesn't shift file data within containers nor alter the original files stored with containers. Instead KE will append mods to the end of containers, update the TOCs (which tells the game to load files at the new positions), and then ensures everything is correctly applied. For mod disabling it reverts the TOC, truncates BINs to original sizes (mods are sliced off), and ensures the BINs are fresh/unmodded copies. It relies on the Backups folder created by KE which essentially backsup all containers' tocs to ensure you have fresh unmodded copies saved, that is where it retrieves the original TOC.

# taildata section

KE will unpack files referenced by the TOCs and assign 22 bytes of taildata to each file, subcontainers are given taildata but not files unpacked from subcontainers since subcontainers have their own TOC (files stored in subcontainers are referenced by the subcontainer TOC while subcontainers themselves and loose files are referenced by the main TOCs in each BIN container). those 22 bytes are used by the Mod Creator and Mod Manager, you must keep the taildata so the Mod Manager can correctly apply/disable mods you create. Those 22 bytes don't alter the usability of files, the game doesn't rely on those 22 bytes only Katsuki Engine does to ensure proper and safe mod applying/disabling.

# Replacing files

If you want to replace loose files make sure to copy the last 22 bytes (taaidata) from the file you're wanting to replace and place it at the end of the file you're wanting to use (i.e., file1.g1t being replaced by new.g1t, copy last 22 bytes of file1.g1t and append to new.g1t). If you want to replace files from a subcontainer, merely replace the files in the subcontainer's folder (each unpacked subcontainer has a folder made that's named after the subcontainer) with the files you want and rebuild the subcontainer with Katsuki Engine's subcontainer rebuild button. Only loose files need the 22 bytes manually handled by you if you're replacing loose files, subcontainers just need rebuilt by KE.

# filename.ref

Make sure that file is placed in the same directory as main.pyw, it's the list of filenames for unpacking files. Don't alter filename.ref unless you know what you're doing.

# Extra Info

Katsuki Engine is named after Katsuki Bakugo from My Hero Academia. This is the start of the modding ecosystem for attack on titan games.
