# Let's Sing Deluxe Mod

This project was made for creating a "deluxe version" for Let's Sing 2025 (it should also work for 2026 and possibly future releases). While this could technically be adapted to work for 2022/23 versions, it's very likely the game will just crash after a certain amount of songs played, so newer versions are highly recommended.

If you own multiple Let's Sing versions you quickly learn it's quite cumbersome switching between different game versions to sing just a few songs you like from each.

Let's Sing games contain 431 unique songs in Nintendo Switch releases with all DLCs as of 2026 and that grows to 576 if you happen to have older Wii versions as well.

This mod let's you put all songs you want into a single game, it can also be paired with the custom songs from Ultrastar converted through [Ultrastar2singit](https://github.com/ratnapatka/ultrastar2singIt)

The script will automatically convert all game files from previous versions to the correct format for the 2025 base game, you can use a simple spreadsheet to mark which game versions and DLCs you own and which songs you would like to keep, letting you save disk space for the jams you actually enjoy singing.

## Credits

<ul>
<li>ratnapatka for the [Ultrastar2singit](https://github.com/ratnapatka/ultrastar2singIt) repo, specially for his contributions on BK2 conversion and general script that served as a base for this one</li>
<li>larsenv for the obscure [mo2mp4](https://github.com/RiiConnect24/mo2mp4) tool to convert wii video format into mp4</li>
</ul>

## Instructions

Before starting the conversion process, you need the actual files from the games you own, for this you will need to dump them, I won't focus on this here as there's plenty of tutorials around for the Switch (e.g. Nxdumptool) or Wii (e.g. dolphin).

You will also need to have the 2025 or 2026 version of the game with the free Song Pack DLC installed (International or Regional versions, e.g. German Hits, French Hits, etc), this is what we will mod through LayeredFS so you have the extra songs in your main game.

Besides the files in this project you will also need to have FFmpeg (I used gyan's release from https://www.gyan.dev/ffmpeg/builds/) in the same folder as the script and [RAD Video Tools](https://www.radgametools.com/bnkdown.htm) installed in your program files.

For base games, cover images are a little cumbersome to get, you will need to extract these with Asset Studio Mod (or similar) from the "resources.assets" file. Unfortunately there's no way to automate this, so instead, in case you don't have expected files in the folder, this will automatically run a Deezer search for alternate cover images.

After you have everything ready, you should have the following folders in place:
videos, vxla, vxla_duet (or vxla_feat), audio, audio_preview, covers

To be clear, this is what your folder should look like

```
LetsSingDeluxeMod/
├── Lets Sing Deluxe DB - CSV.csv
├── songs_XX.json (optional) 
├── lsdeluxe.py
├── MoDecoder/
│   ├── LibMobiclip.dll
│   ├── MobiclipDecoder.exe
│   └── NAudio.dll
├── ffmpeg
│   ├── bin
│   └── ...
├── audio
│   ├── 2BeLoved.ogg
│   ├── 7Years.ogg
│   └── ...
├── audio_preview
│   ├── 2BeLoved_preview.ogg
│   ├── 7Years_preview.ogg
│   └── ...
├── covers
│   ├── 2BeLoved.png
│   ├── 7Years.png
│   └── ...
├── video
│   ├── 2BeLoved.mp4
│   ├── 7Years.mo
│   └── ...
├── vxla
│   ├── 2BeLoved.vxla
│   ├── 7Years.vxla
│   └── ...
└── vxla_duet / vxla_feat
    ├── 2BeLoved.vxla
    ├── 7Years.vxla
    └── ...
```

Make a copy of [this spreadsheet](https://docs.google.com/spreadsheets/d/1O7PlBW7WRpWVQ91WM2VTsidog5oB11HENDqgCjq29vY/copy), this is our song database, you will use this to define which songs you want to export, just click the checkbox for any songs you would like, then go to the main tab and click the "Export DB" button
Also included an offline version of the csv in this repo if you prefer using excel or just want to run the full list

The list will cross check against the files you have in the folder, it will only attempt to convert a specific song if you have all needed files in the folders (video, audio, vxla), otherwise it will skip that song to avoid crashes. To reduce issues for duplicate songs, make sure to only select a single version and avoid selecting songs that are already present in the base game used to apply the mod.

If you want to keep your original DLC songs, copy the songs_XX.json (found in DLCID\romfs) file from the dumped game installation to the project folder.

Run with lsdeluxe.py in the same folder you have the files' folders, the ffmpeg build and the mo2mp4 folders. You should also have RAD Video Tools installed in your computer.

When you run it will ask you for your supported game version, this is only used to define the folder ID for LayeredFS and the JSON song database. Optionally you can choose to skip the original music videos, so it creates the files based on cover images (which is a lot faster and lightweight)

Please be aware depending on the amount of songs, this will probably take a couple hours to finish, however you can stop anytime and resume from the last converted file by running the script again. The script will loop through all files you have in the folders and only convert the ones you have marked in the DB sheet. 

If you have .mo (Wii) video files, these are first converted to .mp4, then all mp4 are converted to bk2. VXLA files also go through some reformatting depending on the version. Remaining files are left untouched.

At the end you should have all files ready in a folder to move to atmosphere Switch folder (e.g. sd:/atmosphere/contents)
