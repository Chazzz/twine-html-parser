# twine-html-parser
Translates the html generated by a twine project into a more readable source format.

### Usage

`main.py [src] [dest]`

where [src] is the location of the file you want to parse and [dest] is the name of the output (parsed) file, e.g.

`main.py twine-project-3.html out.html`

### Contributing
The parser works for many cases but may not work as desired for your specific html file. Additionally, some twine html files have errors like hanging brackets that the parser will likely detect but not autocorrect. Bugs *can* be submitted via the github issue tracker, however pull requests are requested since this branch is otherwise not under active development.
