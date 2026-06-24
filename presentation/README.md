# Presentation TP5

This folder contains a self-contained HTML/CSS/JS presentation for the TP5 project.

## Open the presentation

```bash
xdg-open presentation/index.html
```

Navigation:

- Right arrow / space: next slide
- Left arrow: previous slide
- Home / End: first or last slide

## Export to PDF

```bash
./presentation/export_pdf.sh
```

The generated PDF is written to:

```text
presentation/dist/tp5_presentation.pdf
```

You can also choose a custom output path:

```bash
./presentation/export_pdf.sh presentation/dist/custom_name.pdf
```

The script uses `google-chrome` by default. To use another Chromium-compatible binary:

```bash
CHROME=chromium ./presentation/export_pdf.sh
```
