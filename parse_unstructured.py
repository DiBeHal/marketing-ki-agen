from unstructured.partition.auto import partition

# PDF
if True:
    elements = partition(filename="test.pdf", strategy="fast")
    print("PDF: Anzahl gefundener Elemente:", len(elements))
    for elem in elements[:3]:
        print("---")
        print(elem.text)

# HTML
if False:
    elements = partition(filename="test.html", strategy="fast")
    print("HTML: Anzahl gefundener Elemente:", len(elements))
    for elem in elements[:3]:
        print("---")
        print(elem.text)

# DOCX
if False:
    elements = partition(filename="test.docx", strategy="fast")
    print("DOCX: Anzahl gefundener Elemente:", len(elements))
    for elem in elements[:3]:
        print("---")
        print(elem.text)
