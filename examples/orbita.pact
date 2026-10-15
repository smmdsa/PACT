pact 0.4
format "pact.module/0.4.0"
constants {"budget":6,"per.idea":3}
cells [{"id":"selected","values":[0],"mutable":true},{"id":"lens","values":[0],"mutable":true},{"id":"levels","values":[0,0,0,0,0,0],"mutable":true},{"id":"spent","values":[0],"mutable":true},{"id":"weights","values":[1,4,16,64,256,1024],"mutable":false},{"id":"history","values":[0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],"mutable":true},{"id":"cursor","values":[0],"mutable":true},{"id":"length","values":[1],"mutable":true}]
fn orbit.select
params ["index"]
locals []
result "unit"
writes ["selected"]
z = 0
six = 6
index = local.get index
lower = i32.ge_s index z
upper = i32.lt_s index six
valid = i32.and lower upper
store = set selected z index
checked = guard valid store
return checked
end
fn orbit.lens
params ["value"]
locals []
result "unit"
writes ["lens"]
z = 0
three = 3
value = local.get value
lower = i32.ge_s value z
upper = i32.lt_s value three
valid = i32.and lower upper
store = set lens z value
checked = guard valid store
return checked
end
fn history.record
params []
locals ["i","code","next"]
result "unit"
writes ["history","cursor","length"]
z = 0
one = 1
last = 31
size = 32
i = local.get i
code = local.get code
next = local.get next
clear = local.set code z
level = get levels i
weight = get weights i
term = mul.wrap level weight
sum = add.wrap code term
accumulate = local.set code sum
encode = flow.repeat 6 i accumulate
cursor = get cursor z
following = add.wrap cursor one
prepare = local.set next following
full = i32.ge_s next size
source.index = add.wrap i one
source = get history source.index
copy = set history i source
shift = flow.repeat 31 i copy
clamp = local.set next last
roll = seq shift clamp
idle = seq []
ensure = if full roll idle
save = set history next code
move = set cursor z next
length = add.wrap next one
resize = set length z length
record = seq clear encode prepare ensure save move resize
return record
end
fn history.restore
params []
locals ["i","code","sum"]
result "unit"
writes ["levels","spent"]
z = 0
four = 4
i = local.get i
cursor = get cursor z
packed = get history cursor
capture = local.set code packed
clear = local.set sum z
code = local.get code
sum = local.get sum
weight = get weights i
shifted = i32.div_s code weight
value = i32.rem_s shifted four
restore = set levels i value
add = add.wrap sum value
accumulate = local.set sum add
body = seq restore accumulate
loop = flow.repeat 6 i body
total = set spent z sum
all = seq capture clear loop total
return all
end
fn orbit.adjust
params ["delta"]
locals []
result "unit"
writes ["levels","spent","history","cursor","length"]
z = 0
one = 1
minus = -1
delta = local.get delta
positive = i32.eq delta one
negative = i32.eq delta minus
valid = i32.or positive negative
selected = get selected z
level = get levels selected
next = add.wrap level delta
lower = i32.ge_s next z
limit = const.load per.idea
upper = i32.le_s next limit
level.valid = i32.and lower upper
spent = get spent z
total = add.wrap spent delta
budget = const.load budget
within = i32.le_s total budget
allowed = i32.and level.valid within
store.level = set levels selected next
store.total = set spent z total
record = call history.record []
change = seq store.level store.total record
idle = seq []
attempt = if allowed change idle
checked = guard valid attempt
return checked
end
fn orbit.undo
params []
locals []
result "unit"
writes ["cursor","levels","spent"]
z = 0
one = 1
cursor = get cursor z
available = i32.gt_s cursor z
previous = sub.wrap cursor one
move = set cursor z previous
restore = call history.restore []
change = seq move restore
idle = seq []
attempt = if available change idle
return attempt
end
fn orbit.redo
params []
locals []
result "unit"
writes ["cursor","levels","spent"]
z = 0
one = 1
cursor = get cursor z
length = get length z
next = add.wrap cursor one
available = i32.lt_s next length
move = set cursor z next
restore = call history.restore []
change = seq move restore
idle = seq []
attempt = if available change idle
return attempt
end
fn orbit.reset
params []
locals []
result "unit"
writes ["selected","lens","levels","spent","history","cursor","length"]
reset = reset ["selected","lens","levels","spent","history","cursor","length"]
return reset
end
exports ["orbit.select","orbit.lens","orbit.adjust","orbit.undo","orbit.redo","orbit.reset"]
assets {"palettes":[],"tiles":[]}
presentation {}
tests [{"id":"select.last","function":"orbit.select","args":[5],"set":{},"expect":{"selected":[5]}},{"id":"lens.weave","function":"orbit.lens","args":[2],"set":{},"expect":{"lens":[2]}},{"id":"invest.first","function":"orbit.adjust","args":[1],"set":{},"expect":{"levels":[1,0,0,0,0,0],"spent":[1],"cursor":[1],"length":[2],"history":[0,1]}},{"id":"undo.first","function":"orbit.undo","set":{"levels":[1,0,0,0,0,0],"spent":[1],"cursor":[1],"length":[2],"history":[0,1]},"expect":{"levels":[0,0,0,0,0,0],"spent":[0],"cursor":[0]}},{"id":"redo.first","function":"orbit.redo","set":{"length":[2],"history":[0,1]},"expect":{"levels":[1,0,0,0,0,0],"spent":[1],"cursor":[1]}},{"id":"reset.clean","function":"orbit.reset","set":{"levels":[1,0,0,0,0,0],"spent":[1],"selected":[4],"lens":[2],"cursor":[1],"length":[2],"history":[0,1]},"expect":{"levels":[0,0,0,0,0,0],"spent":[0],"selected":[0],"lens":[0],"cursor":[0],"length":[1],"history":[0,0]}}]
