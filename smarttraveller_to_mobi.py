'''
Smart Traveller information to mobi script.
This script relies on having calibre's ebook-convert inbuilt program.
http://calibre-ebook.com/

Once the webdesigners at smarttraveller.gov.au decide to update their website I'll have to rewrite this to make it work again.

- Hoz, October 2013.

'''

import argparse
import codecs
import lxml.html
import lxml.html.clean
import os
import pickle
import time
import urllib


# Some basic settings
BASE_HTTP = 'http://www.smarttraveller.gov.au'
COUNTRY_LIST_URL = BASE_HTTP + '/zw-cgi/view/Advice/'
COUNTRY_LIST_FILE = 'country_list.pickle'
SAVE_DIR = 'country_html'
TOC_HTML = os.path.join(SAVE_DIR, '_toc.html')
MAIN_HTML = os.path.join(SAVE_DIR, '_main.html')
TOC_HEADER_FILE = "toc_header.html"
EBOOK_OUTPUT_FILE = "smarttraveller%s.mobi" % time.strftime("%b%Y")
EBOOK_COVER = "cover.jpg"
EBOOK_CONVERT = '/Applications/calibre.app/Contents/MacOS/ebook-convert'


def goto_website_return_html(url):
    '''
    Very basic function, could probably do without it.
    '''
    url_handler = urllib.urlopen(url)
    return url_handler.read()


def find_country_list(filename):
    '''
    This function will try to find a pickle file (filename) and try to return a loaded pickle of that.
    If it does not find it, then it goes to smarttraveller and downloads the latest country list.
    '''
    country_list = {}
    try:
        pickle_file = open(filename, 'rb')
        country_list = pickle.load(pickle_file)
        pickle_file.close()
    except:
        # Can't open or use pickle file.
        # Must fetch a new list.
        html = goto_website_return_html(COUNTRY_LIST_URL)
        root = lxml.html.fromstring(html)
        elements = root.find_class('topicRow')
        for element in elements:
            country = element.find_class('hidden')[0].text
            href = BASE_HTTP + element.find_class('topicTitle')[0].get('href')
            issue_date = element.find_class('issueDate')[0].text
            if issue_date:
                issue_date = time.strftime('%d %b %Y', time.strptime(issue_date, '%d/%m/%Y'))
            country_list[country] = {}
            country_list[country]['url'] = href
            country_list[country]['issue_date'] = issue_date
            country_list[country]['safe_name'] = href.split('/')[-1]
            country_list[country]['file_name'] = os.path.join(SAVE_DIR, country_list[country]['safe_name'] + '.html')
        if country_list:
            # Got data now try to save the pickle file.
            pickle_file = open(filename, 'wb')
            pickle.dump(country_list, pickle_file)
            pickle_file.close()
    return country_list


def get_country_html(url):
    '''
    This function goes to the country specific url and grabs the relevant advice html.
    It then also strips away html tags not required for ebook reading.
    '''
    html = goto_website_return_html(url)
    tree = lxml.html.fromstring(html)
    # The advice information is located in the <article id="theArticle"> tag.
    article = tree.xpath("//article[@id='theArticle']")[0]
    try:
        # This has maps and videos, doesn't really place nice with ebooks.
        removeme = article.xpath("//section[@class='mediaFiles']")[0]
        removeme.getparent().remove(removeme)
    except:
        pass
    articlehtml = lxml.html.tostring(article)
    # I don't want extra tags!
    cleaner = lxml.html.clean.Cleaner(safe_attrs_only=True, remove_tags=['a', 'article', 'section', 'span', 'div'])
    cleansed = cleaner.clean_html(articlehtml)
    output_html = cleansed.decode('utf-8')
    return output_html


def build_table_of_contents(country_list):
    '''
    This function builds the top half of the output html. It's a bit of a sloppy way to do this, but it works.
    '''
    header_text = "<!DOCTYPE html><html><head><style type='text/css'>.toc { page-break-after: always; text-indent: 0em; }</style></head><body><h1>Table of Contents</h1><ul id='toc'>"
    output_html = header_text
    for country in sorted(country_list):
        # make sure the links are nice for table of contents building.
        output_html += "<li><a href=\"#%s\">%s</a> (Issued: %s)</li>" % (country_list[country]['safe_name'], country, country_list[country]['issue_date'])
    output_html += "</ul>\n"
    return output_html


def build_big_file(country_list, output_file):
    '''
    Build the big html file (it can be like 3 meg or something).
    This requires a helper function: build_table_of_contents() to build the heading for the output html file.
    Because the file gets large, I decided to make it write to the file on the fly. I didn't want to store all the data into a large variable.
    '''
    outfile = codecs.open(output_file, mode='w', encoding='utf-8')
    header_text = build_table_of_contents(country_list)
    outfile.write(header_text)
    for country in sorted(country_list):
        cfile = codecs.open(country_list[country]['file_name'], mode='r', encoding='utf-8')
        cfile_contents = cfile.read()
        cfile.close()
        # Create a heading with table of contents link.
        # class='chapter' is something that ebook-convert looks for.
        outfile.write("<h1 class='chapter' id='%s'>%s</h1>\n" % (country_list[country]['safe_name'], country))
        # For some reason a div tag doesn't get removed when it's getting 'cleansed'. This replace is a bit of a hack.
        outfile.write(cfile_contents.replace('<div>', '').replace('</div>', ''))
    outfile.write("</body></html>")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='http://smarttraveller.gov.au -> MOBI converter')
    parser.add_argument('-u', help='Update country html files', action='store_true')
    parser.add_argument('-b', help='Build large html file', action='store_true')
    parser.add_argument('-o', help='Output .mobi file', action='store_true')
    args = parser.parse_args()
    # If you didn't specify the script anything to do, print help and quit.
    if not args.u and not args.b and not args.o:
        parser.print_help()
        exit()
    # Keep this in here just to make sure a directory exists.
    if not os.path.isdir(SAVE_DIR):
        os.makedirs(SAVE_DIR)
        print "Created Directory: %s" % os.path.abspath(SAVE_DIR)
    # Populate country_list, either form pickle or loaded form website.
    country_list = find_country_list(COUNTRY_LIST_FILE)
    # error handling, this might be a good indicator if they decide to redesign their website.
    if not country_list:
        print "Problems with finding Country List!"
        exit()

    print "Got country list with %d countries." % len(country_list)

    # Update country html files
    if args.u:
        for country in sorted(country_list):
            html = get_country_html(country_list[country]['url'])
            outfile = codecs.open(country_list[country]['file_name'], mode='w', encoding='utf-8')
            outfile.write(html)
            outfile.close()
            print country_list[country]['file_name'], "written."
        print "------------------------------\nFinished updating html files"

    # Create big html file
    if args.b:
        build_big_file(country_list, MAIN_HTML)
        print "Built output html: %s" % os.path.abspath(MAIN_HTML)

    # Create output mobi file. This takes time.

    if args.o:
        sys_command = "%s %s %s -v -v --max-toc-links=0 --no-chapters-in-toc --output-profile=kindle --change-justification=justify --chapter-mark=both --authors='Australian Government' --book-producer='Hoz' --language='English' --pretty-print --toc-filter=r'*' --title='Smart Traveller (%s)' --pubdate='%s' --comments='This is information taken from smarttraveller.gov.au'" % (EBOOK_CONVERT, os.path.abspath(MAIN_HTML), os.path.abspath(EBOOK_OUTPUT_FILE), time.strftime("%b, %Y"), time.strftime("%d %b %Y"))
        print "Executing: %s" % sys_command
        os.system(sys_command)
