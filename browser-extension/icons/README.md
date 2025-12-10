# Icon Generation

The extension needs PNG icons at the following sizes:

- 16x16 pixels (bookmark-16.png)
- 32x32 pixels (bookmark-32.png)
- 48x48 pixels (bookmark-48.png)
- 96x96 pixels (bookmark-96.png)

## Option 1: Use an online converter

1. Upload `bookmark.svg` to https://cloudconvert.com/svg-to-png
2. Convert to each size
3. Save with the appropriate filenames

## Option 2: Use ImageMagick (if installed)

```bash
cd browser-extension/icons
convert bookmark.svg -resize 16x16 bookmark-16.png
convert bookmark.svg -resize 32x32 bookmark-32.png
convert bookmark.svg -resize 48x48 bookmark-48.png
convert bookmark.svg -resize 96x96 bookmark-96.png
```

## Option 3: Use Inkscape (if installed)

```bash
cd browser-extension/icons
inkscape bookmark.svg --export-filename=bookmark-16.png -w 16 -h 16
inkscape bookmark.svg --export-filename=bookmark-32.png -w 32 -h 32
inkscape bookmark.svg --export-filename=bookmark-48.png -w 48 -h 48
inkscape bookmark.svg --export-filename=bookmark-96.png -w 96 -h 96
```

The extension will work once these PNG files are created.
