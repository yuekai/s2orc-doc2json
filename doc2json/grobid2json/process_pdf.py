import os
import json
import argparse
import time
from bs4 import BeautifulSoup
from typing import Optional, Dict

from doc2json.grobid2json.grobid.grobid_client import GrobidClient
from doc2json.grobid2json.tei_to_json import convert_tei_xml_file_to_s2orc_json, convert_tei_xml_soup_to_s2orc_json

BASE_TEMP_DIR = 'tmp'
BASE_LOG_DIR = 'log'


def process_pdf_stream(input_file: str, sha: str, input_stream: bytes, grobid_config: Optional[Dict] = None) -> Dict:
    """
    Process PDF stream
    :param input_file:
    :param sha:
    :param input_stream:
    :return:
    """
    # process PDF through Grobid -> TEI.XML
    client = GrobidClient(grobid_config)
    tei_text = client.process_pdf_stream(input_file, input_stream, 'temp', "processFulltextDocument")

    # make soup
    soup = BeautifulSoup(tei_text, "xml")

    # get paper
    paper = convert_tei_xml_soup_to_s2orc_json(soup, input_file, sha)

    return paper.release_json('pdf')


def process_pdf_file(
        input_file: str,
        temp_dir: str = None,
        output_dir: str = None,
        grobid_config: Optional[Dict] = None
) -> str:
    """
    Process a PDF file and get JSON representation
    :param input_file:
    :param temp_dir:
    :param output_dir:
    :return:
    """
    if temp_dir is None:
        temp_dir = os.path.join(os.path.dirname(input_file), BASE_TEMP_DIR)
    else:
        os.makedirs(temp_dir, exist_ok=True)

    if output_dir is None:
        output_dir = os.path.dirname(input_file)
    else:
        os.makedirs(output_dir, exist_ok=True)

    # get paper id as the name of the file
    paper_id = '.'.join(input_file.split('/')[-1].split('.')[:-1])
    tei_file = os.path.join(temp_dir, f'{paper_id}.tei.xml')
    output_file = os.path.join(output_dir, f'{paper_id}.pdf.json')

    # check if input file exists and output file doesn't
    if not os.path.exists(input_file):
        raise FileNotFoundError(f"{input_file} doesn't exist")
    if os.path.exists(output_file):
        print(f'{output_file} already exists!')

    # process PDF through Grobid -> TEI.XML
    client = GrobidClient(grobid_config)
    # TODO: compute PDF hash
    # TODO: add grobid version number to output
    client.process_pdf(input_file, temp_dir, "processFulltextDocument")

    # process TEI.XML -> JSON
    assert os.path.exists(tei_file)
    paper = convert_tei_xml_file_to_s2orc_json(tei_file)

    # write to file
    with open(output_file, 'w') as outf:
        json.dump(paper.release_json(), outf, indent=4, sort_keys=False)

    return output_file


def process_dir(
        input_dir: str,
        tmp_dir: str = None,
        out_dir: str = None,
        grobid_config: Optional[Dict] = None
) -> str:
    """
    Process PDF files in a directory
    
    Args:
        input_dir: Directory containing PDF files to process
        tmp_dir: Temporary directory for processing. Defaults to input_dir + 'tmp/'
        out_dir: Output directory for processed files. Defaults to input_dir + 'out/'
        grobid_config: Optional configuration for GROBID
    """
    # Set default values for tmp_dir and out_dir if not provided
    if tmp_dir is None:
        tmp_dir = os.path.join(input_dir, "tmp/")
    if out_dir is None:
        out_dir = input_dir

    # Create temporary and output directories if they don't exist
    os.makedirs(tmp_dir, exist_ok=True)
    os.makedirs(out_dir, exist_ok=True)

    # Loop through files in input_dir
    for filename in os.listdir(input_dir):
        file_path = os.path.join(input_dir, filename)
        # Check if the item is a file and a PDF
        if os.path.isfile(file_path) and filename.lower().endswith('.pdf'):
            # Call process_pdf_file for each PDF
            process_pdf_file(file_path, tmp_dir, out_dir, grobid_config)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Run S2ORC PDF2JSON")
    parser.add_argument("-i", "--input", default=None, help="path to the input PDF file")
    parser.add_argument("-t", "--temp", default=None, help="path to the temp dir for putting tei xml files")
    parser.add_argument("-o", "--output", default=None, help="path to the output dir for putting json files")

    args = parser.parse_args()

    input_path = args.input
    temp_path = args.temp
    output_path = args.output

    start_time = time.time()

    if os.path.isdir(input_path):
        # process all pdf files in the directory
        process_dir(input_path)
    elif os.path.isfile(input_path):
      process_pdf_file(input_path, temp_path, output_path)

    runtime = round(time.time() - start_time, 3)
    print("runtime: %s seconds " % (runtime))
    print('done.')