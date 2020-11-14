# Make a simple text-based graph of prices (or anything else)
import formatting_helpers


def add_y_axis_labels(table_text, min_value, max_value, first_label_overhang):
    min_value = formatting_helpers.prettify_decimals(min_value)
    max_value = formatting_helpers.prettify_decimals(max_value)

    label_text_length = max(len(max_value), len(min_value))

    # format the labels at add at least one space to the end
    min_value = "{:>{}} ".format(min_value, label_text_length)
    max_value = "{:>{}} ".format(max_value, label_text_length)
    # make an empty value (of spaces) with the same width
    empty_space = "{:>{}} ".format("", label_text_length)

    # add max_value to top row of graph
    table_text[0] = list(max_value) + table_text[0]
    # add dummy values to middle rows
    table_text[1:-3] = [list(empty_space) + row for row in table_text[1:-3]]
    # add min_value to last row of graph
    table_text[-3] = list(min_value) + table_text[-3]
    # add dummy values to middle rows
    table_text[-2] = list(empty_space) + table_text[-2]
    # add dummy value to last row of graph, but subtract first_label_overhang chars from padding
    table_text[-1] = list(empty_space[:-first_label_overhang]) + table_text[-1]

    return table_text


def add_x_axis_labels(table_text, labels):
    # first, calculate the locations the x-axis labels should be centered around.
    # if one label, it will just end up in the middle.
    bottom_row_width = len(table_text[-1])
    # first label is centered around 0, since that looks best. that means half of it
    # hangs outside the x-axis, so we calculate that amount (half its length)
    first_label_center = 0
    first_label_overhang = int(len(labels[0]) / 2)
    # last label is centered around the right-most side of the graph. it hangs over the
    # right side in a similar way to first_label
    last_label_center = bottom_row_width - 1
    last_label_overhang = int(len(labels[-1]) / 2)

    # the width of all x-axis labels is equal to x-axis width plus overhangs
    total_label_space_width = bottom_row_width + first_label_overhang + last_label_overhang

    if len(labels) > 2:
        num_slices = len(labels) - 1
        middle_label_centers = [int((n + 1) * bottom_row_width / num_slices) for n in range(num_slices - 1)]

    label_centers = [first_label_center] + middle_label_centers + [last_label_center]
    label_string_buffer = list(' ' * total_label_space_width)
    for idx, label in enumerate(labels):
        this_label_overhang = int(len(label) / 2)
        center = label_centers[idx] + first_label_overhang
        this_label_position = center - this_label_overhang
        label_string_buffer[this_label_position:this_label_position + len(label)] = list(label)

    # spacing_between_labels = int(bottom_row_width / num_slices)
    # previous_label_len = 0
    # label_string_buffer = ""
    # for idx, label in enumerate(labels):
    #     extra_padding = int(spacing_between_labels - (len(label) / 2) - (previous_label_len / 2))
    #     if idx == len(labels)-1:
    #         extra_padding = 0
    #     label_string_buffer += label + '.' * extra_padding
    #     previous_label_len = len(label)


    # last label is aligned to the right-most side of the graph, so we calculate the
    # center-point of the label (half its length) and move to the left by that amount.

    # take the remaining labels and 


    #table_text.append(list(' ' * bottom_row_width))
    table_text.append(list(label_string_buffer))
    table_text[-2][first_label_center] = '|'
    table_text[-2][last_label_center] = '|'
    for center in middle_label_centers:
        table_text[-2][center] = '|'

    # special-case: if 1 label, center it. that is all.
    #if len(labels)
    pass
    return table_text, first_label_overhang


def make_graph(values, labels=[], vertical_resolution=6):
    # Uniswap v2  **0.00067Ξ**   $0.20   34.5Ξ volume
    # ```
    # 0.00070 |
    #         |                 ***
    #         |                *   ****
    #         |        *** ** *
    #         |  ******   *  *
    # 0.00040 |**
    #         |-----------|-----------|
    #       -24h        -12h         now
    # ```
    #assert len(values) > 1, "must have more than 1 value"
    assert vertical_resolution > 2, "vertical_resolution must be > 3"
    #assert len(labels) != 1, "must have 0 labels, or 2+ labels. not 1."

    # list of lists representing the block of text. access with table_text[row][column]
    table_text = [list(" " * len(values)) for _ in range(vertical_resolution)]

    max_value = max(values)
    min_value = min(values)
    value_range = max_value - min_value

    for x_axis_step, value in enumerate(values):
        if value_range == 0:
            # special-case when range is 0: this means all values are the same (straight line)
            value_normalized = 0.5
        else:
            # value_normalized is scaled value in range 0.0 - 1.0
            value_normalized = (value - min_value) / value_range
        #print('value_normalized is', value_normalized)
        vertical_bin = min(int(value_normalized * vertical_resolution), vertical_resolution - 1)
        table_text[vertical_bin][x_axis_step] = '*'

    # flip graph vertically so vertical_bin '0' is now on the bottom
    table_text = table_text[::-1]
    # add y axis
    table_text = [['|'] + row for row in table_text]
    # add x axis
    table_text.append(['|'] + list("-" * len(values)))
    # add x axis labels
    table_text, first_label_overhang = add_x_axis_labels(table_text, labels)
    # add y axis labels
    table_text = add_y_axis_labels(table_text, min_value, max_value, first_label_overhang)

    # TODO: add mode that translates to 'box drawings' characters, which look good in
    # terminal, but not in discord
    # + -> ┼
    # | -> |
    # - -> ─
    # * -> ·

    return '\n'.join(''.join(row) for row in table_text)


if __name__ == "__main__":
    values = range(24)
    labels = ['-24h', '-12h', 'now']
    print(make_graph(values, labels))
    print()
    print()
    values = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    labels = ['-24h', '-12h', 'now']
    print(make_graph(values, labels))
    print()
    print()
    values = [-1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1]
    labels = ['-24h', '-12h', 'now']
    print(make_graph(values, labels))
    print()
    print()
    values = range(40, 70)
    values = [value * 0.0001 for value in values]
    labels = ['-24h', '-12h', 'now']
    print(make_graph(values, labels))
    print()
    print()
    values = [-1]
    labels = ['-24h', '-12h', 'now']
    print(make_graph(values, labels))
    print()
    print()
    values = range(40, 70)
    values = [value * 0.0001 for value in values]
    labels = ['-24h', '-12h', 'now']
    print(make_graph(values, labels))
    print()
    print()
    values = range(40, 70)
    values = [value * 0.0001 for value in values]
    labels = ['AAA', 'BBB', 'CCC', 'DDD', 'EEE']
    print(make_graph(values, labels))
