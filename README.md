# Update

I am no longer using github, I am now using Gitlab. If you want the latest versions of Katsuki Engine then you should keep an eye on the gitlab repository instead https://gitlab.com/PythWare/katsuki-engine

The github version of Katsuki Engine is not the current version of Katsuki Engine, rely on gitlab version instead.

# Katsuki Engine

Katsuki Engine is a GUI toolkit for modding Attack On Titan 2, KE is the foundation of the modding ecosytem for Attack On Titan games. KE can unpack all of the BIN containers, comes with a Mod Creator that turns modded files into AOT2M/AOT2MI mod files (custom mod package/mod installer formats I designed to be used with Katsuki Mod Manager), and a Mod Manager for applying/disabling mods as well as truncating containers back to their original sizes and reverting to original unmoddified versions when disabling all mods.

# What's needed to use

1. Python 3 and Pillow (a Python imaging library). To install pillow open a command prompt and enter `pip install pillow`

2. Place the downloaded files (main.pyw and the Katsuki_Logic folder) in the game's directory (i.e., C:\Program Files (x86)\Steam\steamapps\common\AoT2\LINKDATA)

If you have python 3 and pillow installed you should be able to run Katsuki Engine by double clicking main.pyw.

Don't remove taildata, taildata section will explain this

# Main GUI

KE will unpack the BIN containers, unpack subcontainers, decompress, etc but unpacked files will have incremented filenames while extensions will be based on the file's data.

When unpacking don't assume KE is frozen/stuck if the unpack bar doesn't progress, it isn't. It just takes several minutes to fully unpack/decompress because it's a lot of data being read and a lot of files being unpacked. The speed of unpacking may be affected by if you're unpacking in a HDD or SSD.

<img width="802" height="931" alt="r1" src="https://github.com/user-attachments/assets/3c971280-ce65-4ba1-a215-5f2fc92b76b6" />

# Mod Creator

The Mod Creator turns modded files into aot2m/aot2mi files and allows you to enter metadata like author of the mod, version of mod, description, preview images to be used with the mod to be displayed in the mod manager, selecting modded files to pack into the package, music with your mod release, etc. To briefly explain the Mod Creator, it turns modded files into 1 of 2 things. a mod package (aot2m) which the bulk of future mods will be or a mod installer (aot2mi). Mod packages will be aot2m files while mod installers will be aot2mi files. Mod installers will be used when you release a mod that is single or multi-choice. suppose you want to release a texture mod (you're not limited to texture mods, this is just an example) that upscales a texture, let's say you wanted to give the user the option to select a low, mid, or high resolution version. You'd make it a mod installer release so that the user can choose which version to use. If all you want to do is create a mod that doesn't need options like a translation mod as an example, you'd release the mod as a mod package rather than mod installer.

Other features are Mod Genre tagging added as toggles (All, Texture, Audio, Model, Overhaul as the genres) for Standard Payload and Installer Architect, Build Mod toggles (debug or release versions) added to both as well. I also implemented a custom zlib compression algorithm for text descriptions for mods since some users may type long descriptions. Debug mods have a 5k character limit for descriptions while release Mods will use compression. If a mod is toggled as a release Katsuki will attempt to compress the description with zlib and use KRLE (Katsuki RLE, a custom mini RLE compression algorithm I implemented) on padded data (any unused space leftover if the description doesn't use the full 5k character limit). If the output is smaller then when the mod file is created it'll write the compressed text or if it's larger it'll write the original text and perform KRLE on padded data. So basically, ZLIB and KRLE is used on release tagged mods or just KRLE if ZLIB doesn't actually make the text smaller. 

<img width="1201" height="826" alt="r2" src="https://github.com/user-attachments/assets/e2adfd77-4ab8-4219-b1a1-bc3904e07d87" />
<img width="1197" height="935" alt="r3" src="https://github.com/user-attachments/assets/ab0ccc83-8cf0-4d10-8c66-258b12a04034" />
<img width="1200" height="928" alt="r4" src="https://github.com/user-attachments/assets/07afce67-5c33-43e6-b796-2ceb3f3c9eeb" />

# Mod Manager

KE Mod Manager supports safely applying/disabling mods (aot2m/aot2mi files) as well as resetting the container files with the disable all mods button (truncates containers to original sizes and reverts to fresh unmodded versions), displaying the metadata of mods created, displays preview images of mods, plays music that is included in a mod file, tracks mods currently applied, disable playing music (incase you prefer silence), filter mods by typing or selecting the mod genre toggles, etc. aot2mi files are as explained earlier, mod installers so when you want to install such mods the Katsuki Installer Wizard will appear with the options, descriptions, images, etc of the mod installer.

<img width="1145" height="982" alt="r5" src="https://github.com/user-attachments/assets/052e2ee5-e29f-4011-a426-c4cdf3374c15" />

# Katsuki Installer Wizard

The Installer Wizard will popup when applying AOT2MI mods, mod installer releases. It essentially allows the user to choose what to install from the mod as explained in Mod Creator section.

<img width="900" height="731" alt="k21" src="https://github.com/user-attachments/assets/a787ade8-b581-4ea2-a492-1de0b287f7e9" />
<img width="904" height="737" alt="k22" src="https://github.com/user-attachments/assets/53252b73-e403-4d10-87f4-0630c6f9fe8b" />
<img width="898" height="730" alt="k23" src="https://github.com/user-attachments/assets/619995d4-6918-4c71-ad8b-e359f24ee513" />
<img width="900" height="730" alt="k24" src="https://github.com/user-attachments/assets/3a7144bd-cd84-4e49-b995-c44c9b36a1c3" />
<img width="898" height="726" alt="k25" src="https://github.com/user-attachments/assets/12bd5cd8-b780-48f1-a0ba-8cdebc93068d" />

# How the Mod Manager applies/disables mods

Katsuki Engine doesn't shift file data within containers nor alter the original files stored with containers. Instead KE will append mods to the end of containers, update the TOCs (which tells the game to load files at the new positions), and then ensures everything is correctly applied. For mod disabling it reverts the TOC, truncates BINs to original sizes (mods are sliced off), and ensures the BINs are fresh/unmodded copies. It relies on the Backups folder created by KE which essentially backsup all containers to ensure you have fresh unmodded copies saved, that is where it retrieves the original TOC.

# taildata section

KE will unpack files referenced by the TOCs and assign 22 bytes of taildata to each file, subcontainers are given taildata but not files unpacked from subcontainers since subcontainers have their own TOC (files stored in subcontainers are referenced by the subcontainer TOC while subcontainers themselves and loose files are referenced by the main TOCs in each BIN container). those 22 bytes are used by the Mod Creator and Mod Manager, you must keep the taildata so the Mod Manager can correctly apply/disable mods you create. Those 22 bytes don't alter the usability of files, the game doesn't rely on those 22 bytes only Katsuki Engine does to ensure proper and safe mod applying/disabling.

# Replacing files

If you want to replace loose files make sure to copy the last 22 bytes (taaidata) from the file you're wanting to replace and place it at the end of the file you're wanting to use (i.e., file1.g1t being replaced by new.g1t, copy last 22 bytes of file1.g1t and append to new.g1t). If you want to replace files from a subcontainer, merely replace the files in the subcontainer's folder (each unpacked subcontainer has a folder made that's named after the subcontainer) with the files you want and rebuild the subcontainer with Katsuki Engine's subcontainer rebuild button. Only loose files need the 22 bytes manually handled by you if you're replacing loose files, subcontainers just need rebuilt by KE.

# Extra Info

Katsuki Engine is named after Katsuki Bakugo from My Hero Academia. Also, other GUI tools will be made to make modding easier such as G1T Krieger. This is the start of the modding ecosystem for attack on titan games.
