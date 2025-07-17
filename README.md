Ruminant is a recursive metadata extraction tool.

# What does it do?
Ruminant takes a file as an input and spits out a huge json object that contains all the metadata it extracted from the file. This is done recursively, e.g. by running ruminant again on each file inside a zip file.

# Why the name?
To quote Wikipedia: Ruminants are herbivorous grazing or browsing artiodactyls [...]. The process of rechewing the cud to further break down plant matter and stimulate digestion is called rumination. The word "ruminant" comes from the Latin ruminare, which means "to chew over again".

This tool behaves similarly as extracted blobs themselves can be "chewed over again" (main entrypoint is literally called chew()) in order to recursively extract metadata.

# What can it process?
Ruminant is still in early alpha but it can already process the following file types:
* ZIP files
* DOCX files (needs to be updated)
* PDF files (horribly broken, fuck you Adobe)
* JPEG files
  * EXIF metadata
  * XMP metadata
  * ICC profiles
  * IPTC metadata (I hate you for that one Adobe)
  * Adobe-specific metadata in APP14
* PNG files
  * EXIF metadata
* TIFF files
  * EXIF metadata (EXIF metadata is literally stored in a TIFF file)
* MP4 files
  * XMP metadata
  * AVC1 x264 banners
  * all of the DRM stuff that Netflix puts in their streams
    * CENC
    * PlayReady
    * Widevine

# Ruminant can't parse xyz
Feel free to send me a sample so I can add a parser for it :)

# TODO list
* more file formats
  * MP3
  * WebM
  * WebP
  * Opus
  * Matroska
* fix PDF parsing
* ZIP family detection (e.g. DOCX is also a ZIP file)
