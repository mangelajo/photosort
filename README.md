# PhotoSort Project

## What is PhotoSort?

PhotoSort simplifies your photo inbox, it watches for a set of photo
input directories, to catalog and move into a predefined storage,
it can delete the input or keep it.

It does take care of duplicate files, if there is a duplicate in a
"deletable" source, it will be moved to the duplicates directory
for inspection. If it does found a duplicate in a non deletable source
it will just log it and ignore it.

## Why deletable or not deletable sources?

Non deletables:

My use case is dropbox, mobile phone uploads pictures to dropbox,
the script picks them and packs them, you can decide if they must
be removed from your dropbox account.

Deletables:

An SD card, or a NAS input directory for pictures, you just drag
and drop, and the daemon will discover the new files, process them,
delete them.