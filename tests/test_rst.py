from blender_rag.acquire._rst import rst_to_markdown

SAMPLE = """
************
Introduction
************

See :doc:`Surfaces </modeling/surfaces>` and :ref:`curve-bezier`.

.. figure:: /images/x.png
   :align: center

   A caption.

Section
=======

Body text here.

.. note:: Remember this.

.. toctree::
   :maxdepth: 2

   /modeling/curves/a
   /modeling/curves/b
"""


def test_headers_converted_with_levels():
    md = rst_to_markdown(SAMPLE)
    assert "# Introduction" in md  # over+under '*' -> level 1
    assert "## Section" in md  # underline '=' -> level 2


def test_roles_cleaned_to_visible_text():
    md = rst_to_markdown(SAMPLE)
    assert "Surfaces" in md
    assert ":doc:" not in md
    assert "curve-bezier" in md
    assert "</modeling/surfaces>" not in md


def test_toctree_and_figure_blocks_dropped():
    md = rst_to_markdown(SAMPLE)
    assert "/modeling/curves/a" not in md
    assert "maxdepth" not in md


def test_admonition_content_kept():
    md = rst_to_markdown(SAMPLE)
    assert "Remember this" in md
    assert "Body text here." in md
