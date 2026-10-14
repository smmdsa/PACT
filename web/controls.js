class PactControls {
  constructor(bindings){this.bindings=bindings;this.keys=new Set();this.pointers=new Map();this.pressed=new Set();this.edges=new Set(['jump','action','start'])}
  keyDown(code){if(this.keys.has(code))return;this.keys.add(code);for(const [id,codes]of Object.entries(this.bindings))if(codes.includes(code))this.pressed.add(id)}
  keyUp(code){this.keys.delete(code)}
  pointerDown(pointer,id){this.pointers.set(pointer,id);this.pressed.add(id)}
  pointerUp(pointer){this.pointers.delete(pointer)}
  isHeld(id){return this.bindings[id].some(code=>this.keys.has(code))||[...this.pointers.values()].includes(id)}
  clear(){this.keys.clear();this.pointers.clear();this.pressed.clear()}
  consume(){const values={};for(const id of Object.keys(this.bindings))values[id]=this.edges.has(id)?this.pressed.has(id):this.isHeld(id);this.pressed.clear();return values}
}
