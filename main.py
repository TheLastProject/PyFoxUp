#!/bin/python3

# Copyright (c) 2014 TheLastProject
# This file is part of FoxUp, released under the MIT license
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.


"""
FoxUp
A Python parser for the FoxUp markup language.

To parse a file, run:

    $ python main.py <list of files>

For more information, please check the README.
"""

from sys import argv
try:
    from html import escape
except ImportError:
    def escape(html): return compat_escape(html)

support = []
try:
    from weasyprint import HTML, CSS
    support.append('pdf')
except ImportError:
    pass

def missingparameter(funcname):
    print("Function %s lacks a parameter. Ignoring." % funcname)

"""
Python2 compatibility
"""
def compat_escape(html):
    # Taken from https://wiki.python.org/moin/EscapingHtml
    html_escape_table = {
                        "&": "&amp;",
                        '"': "&quot;",
                        "'": "&apos;",
                        ">": "&gt;",
                        "<": "&lt;",
                        }
    return "".join(html_escape_table.get(c,c) for c in html)

"""
Markup functions
"""
def bold(value, undolist):
    undolist.append("</b>")
    return "<b>", undolist

def italic(value, undolist):
    undolist.append("</em>")
    return "<em>", undolist

def size(value, undolist):
    if value:
        undolist.append("</span>")
        return "<span style='font-size:%spx'>" % value, undolist
    else:
        missingparameter("size")
        return "", undolist

def table(value, undolist):
    return "</td><td>", undolist

def reverse(value, undolist):
    if value:
        return "".join(undolist[len(undolist)-value:]), undolist[:-value]
    else:
        return "".join(undolist), []

functions = {'b': bold,
             'i': italic,
             's': size,
             '|': table,
             'R': reverse
            }

"""
Main functions
"""
def generate_css(title, lang):
    if lang == "nl":
        page = "Pagina"
        of = "van"
    else:
        page = "Page"
        of = "of"

    css = '''
          @page {
            margin: 3cm 2cm; padding-left: 1.5cm;
            @top-center {
              content: "%s";
              vertical-align: bottom; border-bottom: 0.5pt solid; margin-bottom: 0.5cm }
            @bottom-right {
              content: "%s " counter(page) " %s " counter(pages) }}
          body { text-align: justify }
          h1 { -weasy-bookmark-level: none }
          ''' % (title, page, of)
    return css

def write_pdf(html, css, filename):
    HTML(string=html).write_pdf("%s.pdf" % filename, stylesheets=[CSS(string=css)])

def write_html(html, css, filename):
    output = open("%s.html" % filename, "w")
    output.write("<!DOCTYPE html>\n<html>\n<head>\n<style>%s</style>\n</head>\n<body>\n%s\n</body>\n</html>" % (css, html))
    output.close()

def end_document(html, css, filename, toreturn):
    html = "\n".join(html)
    if output_format == "pdf" and toreturn == "file":
        write_pdf(html, css, filename)
    elif toreturn == "file":
        write_html(html, css, filename)
    else:
        return "<!DOCTYPE html>\n<html>\n<head>\n<style>%s</style>\n</head>\n<body>\n%s\n</body>\n</html>" % (css, html)

def get_setting(line):
    if not ":" in line: return None, None # This ends setup
    line = line.split(": ")
    setting = line[0]
    value = line[1]
    return setting, value

def convert_line(line, commandmode, undolist):
    addedhtml = ""
    if commandmode:
        charnumber = 0
        for char in line:
            charnumber += 1
            if char == "*": # Star
                addedhtml += "*"
                break
            elif char == ".": # Dot
                break
            elif char in functions:
                value = []
                while True:
                    tocheck = line[charnumber]
                    try:
                        int(tocheck)
                        value.append(tocheck)
                        charnumber += 1
                    except ValueError:
                        break
                try:
                    value = int("".join(value))
                    charnumber -= len(str(value))
                except ValueError:
                    value = False
                returnedhtml, undolist = functions[char](value, undolist)
                addedhtml += returnedhtml
            else:
                # Remain quiet if it's a stray argument for an unknown command
                try:
                    int(char)
                except ValueError:
                    undolist.append("")
                    print("Unknown command: %s" % char)
        try:
            furtherhtml, commandmode, undolist = convert_line(line[charnumber:], False, undolist)
            return addedhtml + furtherhtml, commandmode, undolist
        except IndexError:
            return addedhtml, commandmode, undolist
    else:
        if not "*" in line: return line, commandmode, undolist
        line = line.split("*", 1)
        addedhtml = line[0]
        furtherhtml, commandmode, undolist = convert_line(line[1], True, undolist)
        return addedhtml + furtherhtml, commandmode, undolist

def specials_before(line, specials):
    if "*|." in line:
        if not "table" in specials:
            specials.append("table")
            return "<table><tr><td>", specials
        else:
            return "<tr><td>", specials
    elif "table" in specials:
        specials.remove("table")
        return "</table>", specials
    
    return "", specials

def specials_after(line, specials):
    if "table" in specials:
        return "</tr>", specials

    return "<br />", specials

def convert(data, datatype="direct"):
    setup = True
    commandmode = False
    specials = []
    undolist = []
    html = ["<p>"]
    css = ""
    # Do not break if users don't set lang or title
    lang = ""
    title = ""
    if datatype == "file":
        with open(data) as f:
            for line in f:
                setup, commandmode, specials, undolist, html, css, lang, title = convert_internal(line, setup, commandmode, specials, undolist, html, css, lang, title)
    else:
        lines = data.split("\n")
        for line in lines:
            setup, commandmode, specials, undolist, html, css, lang, title = convert_internal(line, setup, commandmode, specials, undolist, html, css, lang, title)
   
    endcode = end_document(html, css, data, datatype)
    if datatype != "file":
        return endcode

def convert_internal(line, setup, commandmode, specials, undolist, html, css, lang, title):
    line = escape(line.rstrip('\r\n'))
    if setup:
        setting, value = get_setting(line)
        if setting == "lang":
            lang = value
        elif setting == "title":
            title = value
        elif not setting:
            css = generate_css(title, lang)
            setup = False
            setup, commandmode, specials, undolist, html, css, lang, title = convert_internal(line, setup, commandmode, specials, undolist, html, css, lang, title)
    elif not line:
        if not "table" in specials:
            html.append("</p>\n<p>")
    else:
        # Take care of specials that are to be executed before the main parsing
        addedhtml, specials = specials_before(line, specials)
        html.append(addedhtml)
     
        # Main parsing
        addedhtml, commandmode, undolist = convert_line(line, commandmode, undolist)
        html.append(addedhtml)

        # Take care of specials that are to be executed before the main parsing
        addedhtml, specials = specials_after(line, specials)
        html.append(addedhtml)

    return setup, commandmode, specials, undolist, html, css, lang, title

# Parse options
args = argv[1:]
try:
    index = args.index("--format")
    output_format = args[index+1]
    supported_formats = ["html", "pdf"]
    if output_format not in supported_formats:
        print("E: Unsupported output format. Please choose one of the following formats: %s" % ", ".join(supported_formats))
        exit(1)
    del args[index:index+2]
except ValueError:
    if "pdf" in support:
        output_format = "pdf"
    else:
        print("W: PDF not supported, falling back to HTML output")
        output_format = "html"

for arg in args:
    print("Parsing %s" % arg)
    convert(arg, "file")
