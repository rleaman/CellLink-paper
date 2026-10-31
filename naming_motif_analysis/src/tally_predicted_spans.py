import argparse
import csv
import json
from collections import Counter
import re


DEFAULT_INPUT_FILENAME = "output/predicted_name_motif_spans.json"
DEFAULT_OUTPUT_FILENAME = "output/predicted_span_label_frequencies.tsv"
DEFAULT_OUTPUT2_FILENAME = "output/predicted_name_motif_spans.tsv"
ANNOTATION_PREVIEW_COUNT = 3


def format_identifier_list(identifier_list):
    return ";".join(
        qualifier + ",".join(identifiers)
        for qualifier, identifiers in identifier_list
    )


def get_annotation_key(annotation):
    return (
        annotation["entity_type"],
        format_identifier_list(annotation["identifier_list"]),
    )


def summarize_annotation_counts(annotation_counts):
    sorted_annotations = sorted(
        annotation_counts.items(),
        key=lambda item: (-item[1], item[0][0], item[0][1]),
    )
    if len(sorted_annotations) == 0:
        return ["", "", 0, 0, ""]

    (primary_entity_type, primary_identifiers), primary_frequency = sorted_annotations[0]
    preview_items = sorted_annotations[:ANNOTATION_PREVIEW_COUNT]
    summary = " || ".join(
        f"{entity_type}|{identifiers} [{frequency}]"
        for (entity_type, identifiers), frequency in preview_items
    )
    additional_count = len(sorted_annotations) - len(preview_items)
    if additional_count > 0:
        summary += f" || ... (+{additional_count} more)"
    return [
        primary_entity_type,
        primary_identifiers,
        primary_frequency,
        len(sorted_annotations) - 1,
        summary,
    ]


def main(argv=None):
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    with open(args.input_filename, "r") as file:
        mention_predictions = json.load(file)

    span_label_counts = Counter()
    span_label_example_counts = dict()
    span_label_annotation_counts = dict()
    row_index = 0
    with open(args.mention_output_filename, "w", newline="") as file:
        writer = csv.writer(file, delimiter="\t")
        writer.writerow(
            [
                "row index",
                "span index",
                "mention text",
                "mention frequency",
                "motif text",
                "motif label",
                "primary entity type",
                "primary identifiers",
                "primary annotation frequency",
                #"additional annotation count",
                #"annotation preview",
            ]
        )
        for mention_prediction in mention_predictions:
            mention = mention_prediction["mention"]
            frequency = mention_prediction["frequency"]
            mention_annotation_counts = Counter(
                {
                    get_annotation_key(annotation): annotation["frequency"]
                    for annotation in mention_prediction["annotations"]
                }
            )
            if mention_annotation_counts.total() != frequency:
                raise RuntimeError(
                    f'Annotation frequency does not match mention frequency for "{mention}"'
                )
            annotation_summary = summarize_annotation_counts(mention_annotation_counts)
            #writer.writerow([row_index + 1, 0, mention, frequency, "", "", *annotation_summary])
            entity_type, identifiers, annotation_frequency, additional_annotation_count, _annotation_preview = annotation_summary
            writer.writerow([row_index + 1, 0, mention, "", "",  frequency, entity_type, identifiers, annotation_frequency])
            row_index += 1
            for span_index, span in enumerate(mention_prediction["spans"]):
                text = span["text"].strip()
                if len(text) == 0 or not re.search(r'[A-Za-z]', text):
                    continue
                key = (text, span["label"])
                span_label_counts[key] += frequency
                if not key in span_label_example_counts:
                    span_label_example_counts[key] = Counter()
                span_label_example_counts[key][mention] += frequency
                if not key in span_label_annotation_counts:
                    span_label_annotation_counts[key] = Counter()
                span_label_annotation_counts[key].update(mention_annotation_counts)
                writer.writerow([row_index + 1, span_index + 1, "", text, span["label"]])
                row_index += 1
        

    rows = []
    for (span_text, label), frequency in sorted(span_label_counts.items()):
        annotation_counts = span_label_annotation_counts[(span_text, label)]
        if annotation_counts.total() != frequency:
            raise RuntimeError(
                f'Annotation frequency does not match span frequency for "{span_text}" / "{label}"'
            )
        example = span_label_example_counts[(span_text, label)].most_common()[0][0]
        annotation_summary = summarize_annotation_counts(annotation_counts)
        #rows.append([span_text, label, frequency, example, *annotation_summary])
        entity_type, identifiers, annotation_frequency, additional_annotation_count, _annotation_preview = annotation_summary
        rows.append([span_text, label, frequency, example, entity_type, identifiers])

    rows.sort(key = lambda x: (-x[2], x[0]))
    with open(args.output_filename, "w", newline="") as file:
        writer = csv.writer(file, delimiter="\t")
        writer.writerow(
            [
                "predicted span text",
                "label",
                "frequency",
                "example",
                "primary entity type",
                "primary identifiers",
                "primary annotation frequency",
                #"additional annotation count",
                #"annotation preview",
            ]
        )
        writer.writerows(rows)


def build_arg_parser():
    parser = argparse.ArgumentParser(
        description="Tally predicted motif span text and label frequencies."
    )
    parser.add_argument(
        "--input",
        dest="input_filename",
        default=DEFAULT_INPUT_FILENAME,
        help=f"Prediction span JSON filename (default={DEFAULT_INPUT_FILENAME}).",
    )
    parser.add_argument(
        "--output",
        dest="output_filename",
        default=DEFAULT_OUTPUT_FILENAME,
        help=f"Output TSV filename (default={DEFAULT_OUTPUT_FILENAME}).",
    )
    parser.add_argument(
        "--mention-output",
        dest="mention_output_filename",
        default=DEFAULT_OUTPUT2_FILENAME,
        help=f"Mention and span TSV filename (default={DEFAULT_OUTPUT2_FILENAME}).",
    )
    return parser


if __name__ == "__main__":
    main()
