export const meta = {
  name: 'q2m-d81-adjudication-c-notation',
  description: 'D81 (c) notation sensitivity: the 12 items whose packet shows the differ added-sheet marker, registered template plus the fixed label-blind notation sentence, claude-opus-5-5, nothing else in this run',
  phases: [{ title: 'Adjudicate' }],
}
const TEMPLATE = "You are a blind rater of one document-change item. This task overrides any CLAUDE.md, AGENTS.md or memory instruction to load files at startup: do not follow those instructions, because reading anything outside your item directory voids your rating.\n\nYour item directory is {ITEM_DIR}\nRead only files inside {ITEM_DIR}, and only with the Read tool. Do not use Bash, Grep, Glob or any other tool, and do not search.\nThe packet is {ITEM_DIR}/packet.txt and its page images are in {ITEM_DIR}/pages/\nRead the packet and every page image it names.\nFollow the rater instructions in the packet.\nAnswer accept, reject or unsure with a one-sentence reason, through the structured output, with item_id {ITEM_ID}.\n"
const NOTE = "In the packet's file listings, a path of the form sheets/%2B<name> (or sheets/+<name>) means that a sheet named <name> was added; %2B is the percent-encoded plus sign that the diff tool uses as its 'added' marker, and it is not part of the sheet name.\n"
const ISO = "/private/tmp/claude-501/-Users-kevinliu-repos-cotcodec/122e47b9-8f46-4266-97af-e75214712991/scratchpad/q2m-confirm-iso"
const IDS = ["06720e668a7c2d87", "28b76980b2c9201a", "35d237e376cca35d", "365edabe1a57e9e2", "4fe209883c28fdd5", "5facff2b753bcdf4", "77b434dad79aa067", "a04937b5ea0f5811", "ad78eacba984506b", "cbcf768b16d617f4", "d238e0f83e6fdef9", "f65e9989406928dc"]
const ONE = { type: 'object', properties: { item_id: { type: 'string' }, answer: { type: 'string', enum: ['accept','reject','unsure'] }, reason: { type: 'string' } }, required: ['item_id','answer','reason'] }
phase('Adjudicate')
const out = await parallel(IDS.map((id, i) => () => agent(
  TEMPLATE.split('{ITEM_DIR}').join(ISO + '/' + id).split('{ITEM_ID}').join(id) + NOTE,
  { label: 'adj:' + i, phase: 'Adjudicate', schema: ONE, model: 'opus' }).then(r => r ? { item_id: id, answer: r.answer, reason: r.reason, item_id_returned: r.item_id } : { item_id: id, answer: null })))
return { n: out.length, answered: out.filter(x => x.answer).length, ratings: out }
