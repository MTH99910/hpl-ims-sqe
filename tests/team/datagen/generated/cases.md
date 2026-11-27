# Generated test data (spec sha256 6c13ee4e1eff)

164 cases. EP = equivalence partitioning, BVA = 3-point boundary value analysis.

| Operation | Field | Technique | Class | Value | Expected |
|---|---|---|---|---|---|
| login | `username` | EP | valid:normal | `"ok"` | valid |
| login | `username` | EP | invalid:empty | `""` | invalid |
| login | `username` | EP | invalid:missing | `"__missing__"` | invalid |
| login | `username` | BVA | minLength=1:-1 | `""` | invalid |
| login | `username` | BVA | minLength=1:+0 | `"p"` | valid |
| login | `username` | BVA | minLength=1:+1 | `"pp"` | valid |
| login | `password` | EP | valid:normal | `"ok"` | valid |
| login | `password` | EP | invalid:empty | `""` | invalid |
| login | `password` | EP | invalid:missing | `"__missing__"` | invalid |
| login | `password` | BVA | minLength=1:-1 | `""` | invalid |
| login | `password` | BVA | minLength=1:+0 | `"p"` | valid |
| login | `password` | BVA | minLength=1:+1 | `"pp"` | valid |
| createRequisition | `purpose` | EP | valid:normal | `"Valid text Vali"` | valid |
| createRequisition | `purpose` | EP | invalid:empty | `""` | invalid |
| createRequisition | `purpose` | EP | invalid:whitespace-padded-too-short | `"  aaaaaaaaa  "` | invalid |
| createRequisition | `purpose` | EP | invalid:not-string | `12345` | invalid |
| createRequisition | `purpose` | EP | invalid:missing | `"__missing__"` | invalid |
| createRequisition | `purpose` | BVA | minLength=10:-1 | `"ppppppppp"` | invalid |
| createRequisition | `purpose` | BVA | minLength=10:+0 | `"pppppppppp"` | valid |
| createRequisition | `purpose` | BVA | minLength=10:+1 | `"ppppppppppp"` | valid |
| createRequisition | `notes` | EP | valid:normal | `"ok"` | valid |
| createRequisition | `notes` | EP | valid:very-long (no documented limit) | `"LLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLL...` | valid |
| createRequisition | `notes` | EP | invalid:not-string | `12345` | invalid |
| createRequisition | `items` | EP | valid:non-empty | `{"array_len": 1}` | valid |
| createRequisition | `items` | EP | invalid:not-array | `"not-a-list"` | invalid |
| createRequisition | `items` | EP | invalid:missing | `"__missing__"` | invalid |
| createRequisition | `items` | BVA | minItems=1:-1 | `{"array_len": 0}` | invalid |
| createRequisition | `items` | BVA | minItems=1:+0 | `{"array_len": 1}` | valid |
| createRequisition | `items` | BVA | minItems=1:+1 | `{"array_len": 2}` | valid |
| createRequisition | `items[0].id` | EP | valid:active_item | `{"ref": "active_item"}` | valid |
| createRequisition | `items[0].id` | EP | invalid:inactive_item | `{"ref": "inactive_item"}` | invalid |
| createRequisition | `items[0].id` | EP | invalid:unknown_item | `{"ref": "unknown_item"}` | invalid |
| createRequisition | `items[0].id` | EP | invalid:not-integer | `"abc"` | invalid |
| createRequisition | `items[0].id` | EP | invalid:missing | `"__missing__"` | invalid |
| createRequisition | `items[0].qty` | EP | valid:in-range | `2` | valid |
| createRequisition | `items[0].qty` | EP | invalid:not-integer | `"abc"` | invalid |
| createRequisition | `items[0].qty` | EP | invalid:decimal | `1.5` | invalid |
| createRequisition | `items[0].qty` | EP | invalid:missing | `"__missing__"` | invalid |
| createRequisition | `items[0].qty` | BVA | minimum=1:-1 | `0` | invalid |
| createRequisition | `items[0].qty` | BVA | minimum=1:+0 | `1` | valid |
| createRequisition | `items[0].qty` | BVA | minimum=1:+1 | `2` | valid |
| createRequisition | `items[0].uom` | EP | valid:enum=pcs | `"pcs"` | valid |
| createRequisition | `items[0].uom` | EP | valid:enum=box | `"box"` | valid |
| createRequisition | `items[0].uom` | EP | valid:enum=pack | `"pack"` | valid |
| createRequisition | `items[0].uom` | EP | valid:enum=ream | `"ream"` | valid |
| createRequisition | `items[0].uom` | EP | valid:enum=kg | `"kg"` | valid |
| createRequisition | `items[0].uom` | EP | valid:enum=liter | `"liter"` | valid |
| createRequisition | `items[0].uom` | EP | valid:enum=dozen | `"dozen"` | valid |
| createRequisition | `items[0].uom` | EP | valid:enum=set | `"set"` | valid |
| createRequisition | `items[0].uom` | EP | valid:enum=roll | `"roll"` | valid |
| createRequisition | `items[0].uom` | EP | valid:enum=bottle | `"bottle"` | valid |
| createRequisition | `items[0].uom` | EP | invalid:outside-enum | `"__not_in_enum__"` | invalid |
| createRequisition | `items[0].notes` | EP | valid:normal | `"ok"` | valid |
| createRequisition | `items[0].notes` | EP | valid:very-long (no documented limit) | `"LLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLL...` | valid |
| createRequisition | `items[0].notes` | EP | invalid:not-string | `12345` | invalid |
| updateRequisition | `purpose` | EP | valid:normal | `"Valid text Vali"` | valid |
| updateRequisition | `purpose` | EP | invalid:empty | `""` | invalid |
| updateRequisition | `purpose` | EP | invalid:whitespace-padded-too-short | `"  aaaaaaaaa  "` | invalid |
| updateRequisition | `purpose` | EP | invalid:not-string | `12345` | invalid |
| updateRequisition | `purpose` | EP | invalid:missing | `"__missing__"` | invalid |
| updateRequisition | `purpose` | BVA | minLength=10:-1 | `"ppppppppp"` | invalid |
| updateRequisition | `purpose` | BVA | minLength=10:+0 | `"pppppppppp"` | valid |
| updateRequisition | `purpose` | BVA | minLength=10:+1 | `"ppppppppppp"` | valid |
| updateRequisition | `notes` | EP | valid:normal | `"ok"` | valid |
| updateRequisition | `notes` | EP | valid:very-long (no documented limit) | `"LLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLL...` | valid |
| updateRequisition | `notes` | EP | invalid:not-string | `12345` | invalid |
| updateRequisition | `items` | EP | valid:non-empty | `{"array_len": 1}` | valid |
| updateRequisition | `items` | EP | invalid:not-array | `"not-a-list"` | invalid |
| updateRequisition | `items` | EP | invalid:missing | `"__missing__"` | invalid |
| updateRequisition | `items` | BVA | minItems=1:-1 | `{"array_len": 0}` | invalid |
| updateRequisition | `items` | BVA | minItems=1:+0 | `{"array_len": 1}` | valid |
| updateRequisition | `items` | BVA | minItems=1:+1 | `{"array_len": 2}` | valid |
| updateRequisition | `items[0].id` | EP | valid:active_item | `{"ref": "active_item"}` | valid |
| updateRequisition | `items[0].id` | EP | invalid:inactive_item | `{"ref": "inactive_item"}` | invalid |
| updateRequisition | `items[0].id` | EP | invalid:unknown_item | `{"ref": "unknown_item"}` | invalid |
| updateRequisition | `items[0].id` | EP | invalid:not-integer | `"abc"` | invalid |
| updateRequisition | `items[0].id` | EP | invalid:missing | `"__missing__"` | invalid |
| updateRequisition | `items[0].qty` | EP | valid:in-range | `2` | valid |
| updateRequisition | `items[0].qty` | EP | invalid:not-integer | `"abc"` | invalid |
| updateRequisition | `items[0].qty` | EP | invalid:decimal | `1.5` | invalid |
| updateRequisition | `items[0].qty` | EP | invalid:missing | `"__missing__"` | invalid |
| updateRequisition | `items[0].qty` | BVA | minimum=1:-1 | `0` | invalid |
| updateRequisition | `items[0].qty` | BVA | minimum=1:+0 | `1` | valid |
| updateRequisition | `items[0].qty` | BVA | minimum=1:+1 | `2` | valid |
| updateRequisition | `items[0].uom` | EP | valid:enum=pcs | `"pcs"` | valid |
| updateRequisition | `items[0].uom` | EP | valid:enum=box | `"box"` | valid |
| updateRequisition | `items[0].uom` | EP | valid:enum=pack | `"pack"` | valid |
| updateRequisition | `items[0].uom` | EP | valid:enum=ream | `"ream"` | valid |
| updateRequisition | `items[0].uom` | EP | valid:enum=kg | `"kg"` | valid |
| updateRequisition | `items[0].uom` | EP | valid:enum=liter | `"liter"` | valid |
| updateRequisition | `items[0].uom` | EP | valid:enum=dozen | `"dozen"` | valid |
| updateRequisition | `items[0].uom` | EP | valid:enum=set | `"set"` | valid |
| updateRequisition | `items[0].uom` | EP | valid:enum=roll | `"roll"` | valid |
| updateRequisition | `items[0].uom` | EP | valid:enum=bottle | `"bottle"` | valid |
| updateRequisition | `items[0].uom` | EP | invalid:outside-enum | `"__not_in_enum__"` | invalid |
| updateRequisition | `items[0].notes` | EP | valid:normal | `"ok"` | valid |
| updateRequisition | `items[0].notes` | EP | valid:very-long (no documented limit) | `"LLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLL...` | valid |
| updateRequisition | `items[0].notes` | EP | invalid:not-string | `12345` | invalid |
| hodDecision | `action` | EP | valid:enum=authorized | `"authorized"` | valid |
| hodDecision | `action` | EP | valid:enum=sent_back | `"sent_back"` | valid |
| hodDecision | `action` | EP | valid:enum=rejected | `"rejected"` | valid |
| hodDecision | `action` | EP | invalid:outside-enum | `"__not_in_enum__"` | invalid |
| hodDecision | `action` | EP | invalid:missing | `"__missing__"` | invalid |
| hodDecision | `status` | EP | valid:enum=pending_hod | `"pending_hod"` | valid |
| hodDecision | `status` | EP | valid:enum=draft | `"draft"` | valid |
| hodDecision | `status` | EP | valid:enum=sent_back | `"sent_back"` | valid |
| hodDecision | `status` | EP | valid:enum=authorized | `"authorized"` | valid |
| hodDecision | `status` | EP | valid:enum=rejected | `"rejected"` | valid |
| hodDecision | `status` | EP | valid:enum=issued | `"issued"` | valid |
| hodDecision | `status` | EP | valid:enum=cancelled | `"cancelled"` | valid |
| hodDecision | `status` | EP | invalid:outside-enum | `"__not_in_enum__"` | invalid |
| hodDecision | `status` | EP | invalid:missing | `"__missing__"` | invalid |
| hodDecision | `notes` | EP | valid:normal | `"ok"` | valid |
| hodDecision | `notes` | EP | valid:very-long (no documented limit) | `"LLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLL...` | valid |
| hodDecision | `rejection_reason` | EP | valid:normal | `"ok"` | valid |
| hodDecision | `rejection_reason` | EP | invalid:empty | `""` | invalid |
| hodDecision | `rejection_reason` | BVA | minLength=1:-1 | `""` | invalid |
| hodDecision | `rejection_reason` | BVA | minLength=1:+0 | `"p"` | valid |
| hodDecision | `rejection_reason` | BVA | minLength=1:+1 | `"pp"` | valid |
| hodDecision | `sent_back_reason` | EP | valid:normal | `"ok"` | valid |
| hodDecision | `sent_back_reason` | EP | invalid:empty | `""` | invalid |
| hodDecision | `sent_back_reason` | BVA | minLength=1:-1 | `""` | invalid |
| hodDecision | `sent_back_reason` | BVA | minLength=1:+0 | `"p"` | valid |
| hodDecision | `sent_back_reason` | BVA | minLength=1:+1 | `"pp"` | valid |
| issueItems | `items-TOTAL_FORMS` | EP | valid:in-range | `1` | valid |
| issueItems | `items-TOTAL_FORMS` | EP | invalid:not-integer | `"abc"` | invalid |
| issueItems | `items-TOTAL_FORMS` | EP | invalid:decimal | `1.5` | invalid |
| issueItems | `items-TOTAL_FORMS` | EP | invalid:missing | `"__missing__"` | invalid |
| issueItems | `items-INITIAL_FORMS` | EP | valid:in-range | `1` | valid |
| issueItems | `items-INITIAL_FORMS` | EP | invalid:not-integer | `"abc"` | invalid |
| issueItems | `items-INITIAL_FORMS` | EP | invalid:decimal | `1.5` | invalid |
| issueItems | `items-INITIAL_FORMS` | EP | invalid:missing | `"__missing__"` | invalid |
| issueItems | `items-0-id` | EP | valid:own_line | `{"ref": "own_line"}` | valid |
| issueItems | `items-0-id` | EP | invalid:other_requisition_line | `{"ref": "other_requisition_line"}` | invalid |
| issueItems | `items-0-id` | EP | invalid:unknown_line | `{"ref": "unknown_line"}` | invalid |
| issueItems | `items-0-id` | EP | invalid:not-integer | `"abc"` | invalid |
| issueItems | `items-0-id` | EP | invalid:missing | `"__missing__"` | invalid |
| issueItems | `items-0-quantity_issued` | EP | valid:in-range | `1` | valid |
| issueItems | `items-0-quantity_issued` | EP | invalid:not-integer | `"abc"` | invalid |
| issueItems | `items-0-quantity_issued` | EP | invalid:decimal | `1.5` | invalid |
| issueItems | `items-0-quantity_issued` | EP | invalid:missing | `"__missing__"` | invalid |
| issueItems | `items-0-quantity_issued` | BVA | minimum=0:-1 | `-1` | invalid |
| issueItems | `items-0-quantity_issued` | BVA | minimum=0:+0 | `0` | valid |
| issueItems | `items-0-quantity_issued` | BVA | minimum=0:+1 | `1` | valid |
| issueItems | `items-0-quantity_issued` | BVA | maximum-ref=line.quantity_requested:-1 | `{"ref": "line.quantity_requested", "o...` | valid |
| issueItems | `items-0-quantity_issued` | BVA | maximum-ref=line.quantity_requested:+0 | `{"ref": "line.quantity_requested", "o...` | valid |
| issueItems | `items-0-quantity_issued` | BVA | maximum-ref=line.quantity_requested:+1 | `{"ref": "line.quantity_requested", "o...` | invalid |
| issueItems | `items-0-quantity_issued` | BVA | maximum-ref=item.quantity_total:-1 | `{"ref": "item.quantity_total", "offse...` | valid |
| issueItems | `items-0-quantity_issued` | BVA | maximum-ref=item.quantity_total:+0 | `{"ref": "item.quantity_total", "offse...` | valid |
| issueItems | `items-0-quantity_issued` | BVA | maximum-ref=item.quantity_total:+1 | `{"ref": "item.quantity_total", "offse...` | invalid |
| issueItems | `items-0-notes` | EP | valid:normal | `"ok"` | valid |
| issueItems | `items-0-notes` | EP | valid:very-long (no documented limit) | `"LLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLL...` | valid |
| itemSuggestions | `q` | EP | valid:normal | `"ok"` | valid |
| itemSuggestions | `q` | EP | valid:very-long (no documented limit) | `"LLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLL...` | valid |
| itemSuggestions | `q` | EP | invalid:not-string | `12345` | invalid |
| itemSuggestions | `type` | EP | valid:enum=stationery | `"stationery"` | valid |
| itemSuggestions | `type` | EP | valid:enum=housekeeping | `"housekeeping"` | valid |
| itemSuggestions | `type` | EP | invalid:outside-enum | `"__not_in_enum__"` | invalid |
| itemDetails | `q` | EP | valid:normal | `"ok"` | valid |
| itemDetails | `q` | EP | valid:very-long (no documented limit) | `"LLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLLL...` | valid |
| itemDetails | `q` | EP | invalid:not-string | `12345` | invalid |
| itemDetails | `type` | EP | valid:enum=stationery | `"stationery"` | valid |
| itemDetails | `type` | EP | valid:enum=housekeeping | `"housekeeping"` | valid |
| itemDetails | `type` | EP | invalid:outside-enum | `"__not_in_enum__"` | invalid |
