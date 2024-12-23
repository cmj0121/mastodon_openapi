#! /usr/bin/env python
import argparse

from src.handler import run


def main():
    baseurl = "https://docs.joinmastodon.org"

    parser = argparse.ArgumentParser(description="Mastodon OpenAPI Spec Generator")
    parser.add_argument("baseurl", default=baseurl, nargs="?", help="The base url of the Mastodon API documentation")
    parser.add_argument("-o", "--output", help="The output file to write the OpenAPI spec to")

    args = parser.parse_args()
    text = run(args.baseurl)

    match args.output:
        case None:
            print(text)
        case _:
            with open(args.output, "w") as file:
                file.write(text)


if __name__ == "__main__":
    main()
