#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2020 Richard Hughes <richard@hughsie.com>
#
# SPDX-License-Identifier: GPL-2.0+

from typing import Optional, List

from lxml import etree as ET

from lvfs.util import _check_is_markdown_li

from .models import Claim


def _add_problem(
    problems: List[Claim], description: str, line: Optional[str] = None
) -> None:
    for problem in problems:
        if problem.description.split("\n")[0] == description:
            return
    if line:
        description += "\n{}".format(line)
    problems.append(
        Claim(
            kind="invalid-release-description",
            icon="warning",
            summary="Invalid release description",
            description=description,
        )
    )


def _check_both(problems: List[Claim], txt: str) -> None:
    if txt.isupper():
        _add_problem(problems, "Uppercase only sentences are not allowed", txt)
    if txt.find("http://") != -1 or txt.find("https://") != -1:
        _add_problem(problems, "Links cannot be included in update descriptions", txt)

    # look for tokens that should not exist in the update description
    txt = txt.upper().replace('_', '-')
    if txt.find("CVE-") != -1 or txt.find("CVE201") != -1 or txt.find("CVE202") != -1:
        _add_problem(problems, "CVEs in update description")
    if txt.find("LEN-") != -1:
        _add_problem(problems, "Lenovo-specific security advisory tag in description")
    if txt.find("DSA-") != -1:
        _add_problem(problems, "Dell-specific security advisory tag in description")
    if txt.find("INTEL-SA-") != -1:
        _add_problem(problems, "Intel-specific security advisory tag in description")
    if txt.find("INTEL-TA-") != -1:
        _add_problem(problems, "Intel-specific technical advisory tag in description")
    if txt.find("REMOVE-ME") != -1:
        _add_problem(problems, "Description should be checked after importing issues")


def _check_is_fake_li(txt: str) -> bool:
    for line in txt.split("\n"):
        if _check_is_markdown_li(line):
            return True
    return False


def _check_para(problems: List[Claim], txt: str):
    _check_both(problems, txt)
    if txt.startswith("[") and txt.endswith("]"):
        _add_problem(problems, 'Paragraphs cannot start and end with "[]"', txt)
    if txt.startswith("(") and txt.endswith(")"):
        _add_problem(problems, 'Paragraphs cannot start and end with "()"', txt)
    if _check_is_fake_li(txt):
        _add_problem(problems, "Paragraphs cannot start with list elements", txt)
    if txt.find(".BLD") != -1 or txt.find("changes.new") != -1:
        _add_problem(problems, "Do not refer to BLD or changes.new release notes", txt)
    if len(txt) > 300:
        _add_problem(
            problems,
            "Paragraph too long, limit is 300 chars and was %i" % len(txt),
            txt,
        )
    if len(txt) < 12:
        _add_problem(
            problems,
            "Paragraph too short, minimum is 12 chars and was %i" % len(txt),
            txt,
        )


def _check_li(problems: List[Claim], txt: str):
    _check_both(problems, txt)
    if txt in ("Nothing.", "Not applicable."):
        _add_problem(problems, "List element cannot be empty", txt)
    if _check_is_fake_li(txt):
        _add_problem(problems, "List element cannot start with bullets", txt)
    if txt.find(".BLD") != -1:
        _add_problem(problems, "Do not refer to BLD notes", txt)
    if txt.find("Fix the return code from GetHardwareVersion") != -1:
        _add_problem(problems, "Do not use the example update notes!", txt)
    if len(txt) > 300:
        _add_problem(
            problems,
            "List element too long, limit is 300 chars and was %i" % len(txt),
            txt,
        )
    if len(txt) < 5:
        _add_problem(
            problems,
            "List element too short, minimum is 5 chars and was %i" % len(txt),
            txt,
        )


def _get_update_description_problems(root: ET.SubElement) -> List[Claim]:
    problems: List[Claim] = []
    n_para = 0
    n_li = 0
    for n in root:
        if n.tag == "p":
            _check_para(problems, n.text)
            n_para += 1
        elif n.tag == "ul" or n.tag == "ol":
            for c in n:
                if c.tag == "li":
                    _check_li(problems, c.text)
                    n_li += 1
                else:
                    _add_problem(problems, "Invalid XML tag", "<%s>" % c.tag)
        else:
            _add_problem(problems, "Invalid XML tag", "<%s>" % n.tag)
    if n_para > 5:
        _add_problem(problems, "Too many paragraphs, limit is 5 and was %i" % n_para)
    if n_li > 20:
        _add_problem(problems, "Too many list elements, limit is 20 and was %i" % n_li)
    if n_para < 1:
        _add_problem(problems, "Not enough paragraphs, minimum is 1")
    return problems
