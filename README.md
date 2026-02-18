# Katsuki Engine

Katsuki Engine is a GUI toolkit for modding Attack On Titan 2 and soon Attack On Titan 1, KE is the foundation of the modding ecosytem for Attack On Titan games. KE can unpack all of the BIN containers, comes with a Mod Creator that turns modded files into AOT2M/AOT2MI mod files (custom mod package/mod installer formats I designed to be used with Katsuki Mod Manager), and a Mod Manager for applying/disabling mods as well as truncating containers back to their original sizes and reverting to original unmoddified versions when disabling all mods.

Katsuki Engine is not yet ready to release but it's close to being ready

# Main GUI

<img width="799" height="831" alt="k8" src="https://github.com/user-attachments/assets/3261979e-ae13-4cbe-ae25-2dd526730cac" />

# Mod Creator

The Mod Creator turns modded files into aot2m/aot2mi files and allows you to enter metadata like author of the mod, version of mod, description, preview images to be used with the mod to be displayed in the mod manager, selecting modded files to pack into the package, etc. Also supports including music with your mod release. I thought it would be rad to have a song play when a mod is selected in the mod manager. To briefly explain the Mod Creator, it turns modded files into 1 of 2 things. a mod package (aot2m) which the bulk of future mods will be or a mod installer (aot2mi). Mod packages will be aot2m files while mod installers will be aot2mi files. Mod installers will be used when you release a mod that is single or multi-choice. suppose you want to release a texture mod (you're not limited to texture mods, this is just an example) that upscales a texture, let's say you wanted to give the user the option to select a low, mid, or high resolution version. You'd make it a mod installer release so that the user can choose which version to use. If all you want to do is create a mod that doesn't need options like a translation mod as an example, you'd release the mod as a mod package rather than mod installer. 

<img width="1201" height="837" alt="k2" src="https://github.com/user-attachments/assets/4da77fcc-f504-45ff-a44f-0e4243c48949" />
<img width="1193" height="828" alt="k1" src="https://github.com/user-attachments/assets/d60ff929-ffb7-419f-99eb-74dd2c8bb25a" />
<img width="1203" height="829" alt="k3" src="https://github.com/user-attachments/assets/2ea45ce3-a4e5-4ce6-b1d1-deb803920426" />
<img width="1202" height="829" alt="k4" src="https://github.com/user-attachments/assets/13b206a2-1338-4736-b699-8e85610596a8" />

# Mod Manager

KE Mod Manager supports safely applying/disabling mods (aot2m/aot2mi files) as well as resetting the container files with the disable all mods button (truncates containers to original sizes and reverts to fresh unmodded versions), displaying the metadata of mods created, displays preview images of mods, plays music that is included in a mod file, tracks mods currently applied, disable playing music (incase you prefer silence), etc. aot2mi files are as explained earlier, mod installers so when you want to install such mods the Katsuki Installer Wizard will appear with the options, descriptions, images, etc of the mod installer.

Another feature of KE Mod Manager is mod collision detection, if a collision is detected KE will try to resolve the collision.

<img width="1139" height="972" alt="k9" src="https://github.com/user-attachments/assets/d81e242a-c2c4-4982-aba5-662070321888" />

# Katsuki Installer Wizard

The Installer Wizard will popup when applying AOT2MI mods, mod installer releases. It essentially allows the user to choose what to install from the mod as explained in Mod Creator section.

<img width="1838" height="993" alt="k5" src="https://github.com/user-attachments/assets/94a1d6db-3f09-4728-8a8c-c2ea8d6e447e" />
<img width="1896" height="979" alt="k7" src="https://github.com/user-attachments/assets/50269397-bd78-4961-83e5-ff860c43f736" />
<img width="1898" height="981" alt="k6" src="https://github.com/user-attachments/assets/6ce6fed2-80e6-4188-ad5d-4f37a0f10a00" />

# Extra Info

Katsuki Engine is namjed after Katsuki Bakugo from My Hero Academia. Also, other GUI tools will be made to make modding easier such as G1T Krieger. This is the start of the modding ecosystem for attack on titan games.
