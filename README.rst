WTFamily
~~~~~~~~

Back-end, RESTful API service for WTFamily. 

WTFamily is a genealogical research software.

See WTFamily_ for high-level overview and instructions.

About this repository
=====================

This repo used to be *the* repo for WTFamily and the original scope of the whole project was quite different.

It used to be a YAML-based publishing system (having everything editable manually or via special commands + changes tracked with Git) with a data structure inspired by GRAMPS. This nice idea then clashed with reality and was eventually proven to be unrealistic due to a number of reasons, although in general this concept worked perfectly for `Timetra`_ diary.

Afterwards the focus was shifted to being a user-friendly app with a companion role to GRAMPS with as full import/export as possible (i.e. you should be able to create everything in either WTFamily or GRAMPS, import to the other one with minimal losses and easily keep the two apps in sync).

The original deprecated web UI still remains in the codebase and even has a few features not yet implemented in the `modern UI`_ (as of 2021).

Eventually this repo should be much simpler, all user-facing code moved to the modern UI and all high-level docs/TODOs moved to the umbrella repo.

If interested, drop me a message.

.. _WTFamily: https://github.com/neithere/wtfamily
.. _Modern UI: https://github.com/neithere/wtfamily-fe
.. _Timetra: https://github.com/neithere/timetra.diary
