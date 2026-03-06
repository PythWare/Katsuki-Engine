# Katsuki Engine

Katsuki Engine is a GUI toolkit for modding Attack On Titan 2 and soon Attack On Titan 1, KE is the foundation of the modding ecosytem for Attack On Titan games. KE can unpack all of the BIN containers, comes with a Mod Creator that turns modded files into AOT2M/AOT2MI mod files (custom mod package/mod installer formats I designed to be used with Katsuki Mod Manager), and a Mod Manager for applying/disabling mods as well as truncating containers back to their original sizes and reverting to original unmoddified versions when disabling all mods.

Katsuki Engine is not yet ready to release but it's close to being ready

# Main GUI
<img width="797" height="831" alt="k31" src="https://github.com/user-attachments/assets/7e569daf-2a61-41cd-a63b-d75bb185783b" />

# Mod Creator

The Mod Creator turns modded files into aot2m/aot2mi files and allows you to enter metadata like author of the mod, version of mod, description, preview images to be used with the mod to be displayed in the mod manager, selecting modded files to pack into the package, etc. Also supports including music with your mod release. I thought it would be rad to have a song play when a mod is selected in the mod manager. To briefly explain the Mod Creator, it turns modded files into 1 of 2 things. a mod package (aot2m) which the bulk of future mods will be or a mod installer (aot2mi). Mod packages will be aot2m files while mod installers will be aot2mi files. Mod installers will be used when you release a mod that is single or multi-choice. suppose you want to release a texture mod (you're not limited to texture mods, this is just an example) that upscales a texture, let's say you wanted to give the user the option to select a low, mid, or high resolution version. You'd make it a mod installer release so that the user can choose which version to use. If all you want to do is create a mod that doesn't need options like a translation mod as an example, you'd release the mod as a mod package rather than mod installer.

Other features are Mod Genre tagging added as toggles (All, Texture, Audio, Model, Overhaul as the genres) for Standard Payload and Installer Architect, Build Mod toggles (debug or release versions) added to both as well. I also implemented a custom zlib compression algorithm for text descriptions for mods since some users may type long descriptions. Debug mods have a 5k character limit for descriptions while release Mods will use compression. If a mod is toggled as a release Katsuki will attempt to compress the description with zlib and use KRLE (Katsuki RLE, a custom mini RLE compression algorithm I implemented) on padded data (any unused space leftover if the description doesn't use the full 5k character limit). If the output is smaller then when the mod file is created it'll write the compressed text or if it's larger it'll write the original text and perform KRLE on padded data. So basically, ZLIB and KRLE is used on release tagged mods or just KRLE if ZLIB doesn't actually make the text smaller. 

<img width="1201" height="837" alt="k2" src="https://github.com/user-attachments/assets/4da77fcc-f504-45ff-a44f-0e4243c48949" />
<img width="1193" height="828" alt="k1" src="https://github.com/user-attachments/assets/d60ff929-ffb7-419f-99eb-74dd2c8bb25a" />
<img width="1203" height="829" alt="k3" src="https://github.com/user-attachments/assets/2ea45ce3-a4e5-4ce6-b1d1-deb803920426" />
<img width="1202" height="829" alt="k4" src="https://github.com/user-attachments/assets/13b206a2-1338-4736-b699-8e85610596a8" />

# Mod Manager

KE Mod Manager supports safely applying/disabling mods (aot2m/aot2mi files) as well as resetting the container files with the disable all mods button (truncates containers to original sizes and reverts to fresh unmodded versions), displaying the metadata of mods created, displays preview images of mods, plays music that is included in a mod file, tracks mods currently applied, disable playing music (incase you prefer silence), filter mods by typing or selecting the mod genre toggles, etc. aot2mi files are as explained earlier, mod installers so when you want to install such mods the Katsuki Installer Wizard will appear with the options, descriptions, images, etc of the mod installer.

Another feature of KE Mod Manager is mod collision detection, if a collision is detected KE will try to resolve the collision.

<img width="1150" height="985" alt="k29" src="https://github.com/user-attachments/assets/60519dbb-a4f0-4655-b6b0-03d1a1973cd7" />
<img width="1147" height="983" alt="k30" src="https://github.com/user-attachments/assets/80925a36-d8f5-46ab-ab0d-dd9bc0396619" />


# Katsuki Installer Wizard

The Installer Wizard will popup when applying AOT2MI mods, mod installer releases. It essentially allows the user to choose what to install from the mod as explained in Mod Creator section.

<img width="900" height="731" alt="k21" src="https://github.com/user-attachments/assets/a787ade8-b581-4ea2-a492-1de0b287f7e9" />
<img width="904" height="737" alt="k22" src="https://github.com/user-attachments/assets/53252b73-e403-4d10-87f4-0630c6f9fe8b" />
<img width="898" height="730" alt="k23" src="https://github.com/user-attachments/assets/619995d4-6918-4c71-ad8b-e359f24ee513" />
<img width="900" height="730" alt="k24" src="https://github.com/user-attachments/assets/3a7144bd-cd84-4e49-b995-c44c9b36a1c3" />
<img width="898" height="726" alt="k25" src="https://github.com/user-attachments/assets/12bd5cd8-b780-48f1-a0ba-8cdebc93068d" />


# Extra Info

Katsuki Engine is named after Katsuki Bakugo from My Hero Academia. Also, other GUI tools will be made to make modding easier such as G1T Krieger. This is the start of the modding ecosystem for attack on titan games.
