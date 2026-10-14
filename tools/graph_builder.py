class Function:
    def __init__(self, name, params=(), result='unit', locals_=()):
        self.name, self.params, self.result = name, list(params), result
        self.locals, self.nodes, self.ids = list(locals_), [], set()

    def node(self, op, **fields):
        key = f'n{len(self.nodes):04d}'
        self.nodes.append({'id': key, 'op': op, **fields})
        self.ids.add(key)
        return key

    def value(self, value):
        return value if isinstance(value, str) and value in self.ids else self.c(value)

    def c(self, value):
        return self.node('const.load', name=value) if isinstance(value,str) else self.node('i32.const',value=value)

    def local(self, name): return self.node('local.get',name=name)
    def assign(self,name,value): return self.node('local.set',name=name,args=[self.value(value)])
    def get(self,cell,index=0): return self.node('state.load',cell=cell,args=[self.value(index)])
    def put(self,cell,value,index=0): return self.node('state.store',cell=cell,args=[self.value(index),self.value(value)])
    def call(self,name,*args): return self.node('call',target=name,args=[self.value(arg) for arg in args])
    def op(self,name,*args): return self.node('i32.'+name,args=[self.value(arg) for arg in args])
    def add(self,a,b): return self.op('add_wrap',a,b)
    def sub(self,a,b): return self.op('sub_wrap',a,b)
    def mul(self,a,b): return self.op('mul_wrap',a,b)
    def div(self,a,b): return self.op('div_s',a,b)
    def eq(self,a,b): return self.op('eq',a,b)
    def ne(self,a,b): return self.op('ne',a,b)
    def lt(self,a,b): return self.op('lt_s',a,b)
    def gt(self,a,b): return self.op('gt_s',a,b)
    def le(self,a,b): return self.op('le_s',a,b)
    def ge(self,a,b): return self.op('ge_s',a,b)
    def and_(self,*args):
        value=self.value(args[0])
        for arg in args[1:]: value=self.op('and',value,arg)
        return value
    def or_(self,*args):
        value=self.value(args[0])
        for arg in args[1:]: value=self.op('or',value,arg)
        return value
    def if_(self,condition,yes,no=None):
        if no is None: no=self.seq()
        return self.node('flow.if',args=[self.value(condition),self.value(yes),self.value(no)])
    def seq(self,*steps): return self.node('flow.sequence',args=list(steps))
    def repeat(self,count,counter,body): return self.node('flow.repeat',count=count,counter=counter,args=[body])
    def abs(self,value): return self.call('math.abs',value)
    def min(self,a,b): return self.call('math.min',a,b)
    def max(self,a,b): return self.call('math.max',a,b)

    def finish(self,entry):
        indexed={node['id']:node for node in self.nodes}
        used=set()
        def visit(key):
            if key in used:return
            used.add(key)
            for ref in indexed[key].get('args',[]):visit(ref)
        visit(entry)
        return {'id':self.name,'params':self.params,'locals':self.locals,'result':self.result,
                'writes':[],'entry':entry,'nodes':[node for node in self.nodes if node['id'] in used]}


def declare_writes(functions):
    indexed={fn['id']:fn for fn in functions}
    done={}
    def visit(key):
        if key in done:return done[key]
        writes=set()
        for node in indexed[key]['nodes']:
            if node['op']=='state.store':writes.add(node['cell'])
            elif node['op']=='call':writes.update(visit(node['target']))
        done[key]=writes
        indexed[key]['writes']=sorted(writes)
        return writes
    for key in indexed:visit(key)
