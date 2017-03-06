#=========================================================================
# MethodComponent.py
#=========================================================================
# At this level, we add methods, and partial constraints on top of update
# blocks and total constraints, to improve productivity.
# Two update blocks communicate via methods of the same component.
# A partial constraint is specified between one update block and one
# method, or two methods. PyMTL will try to chain partial constraints to
# produce total constraints.

import re, inspect, ast
p = re.compile('( *(@|def))')
from collections import defaultdict, deque

from UpdateComponent import UpdateComponent, U, _int

class M(object): # method wrapper
  def __init__( self, func ):
    self.func = func
  def __lt__( self, other ):
    return (self, other)
  def __gt__( self, other ):
    return (other, self)
  def __call__( self ):
    self.func()

class MethodComponent( UpdateComponent ):

  def __new__( cls, *args, **kwargs ):
    inst = super( MethodComponent, cls ).__new__( cls, *args, **kwargs )

    inst._blkid_methods = defaultdict(list)
    inst._method_blks   = defaultdict(list)
    inst._predecessors  = defaultdict(set)
    inst._successors    = defaultdict(set)
    return inst

  # Override
  def update( s, blk ):
    super( MethodComponent, s ).update( blk )

    # Parse the ast to extract method calls

    blk_id = id(blk)
    tree = type(s)._blkid_ast[ blk_id ]

    for node in ast.walk(tree):
      # Check if the node is a function call and the function name is not
      # not min,max,etc; it should be a component method call s.x.y.z()

      if isinstance( node, ast.Call ) and not isinstance( node.func, ast.Name ):

        t = node.func.value
        obj_name = []
        while hasattr( t, "value" ): # don't record the last "s."
          obj_name.append( t.attr )
          t = t.value

        obj_name.reverse()
        method_name = node.func.attr
        s._blkid_methods[ blk_id ].append( (obj_name, method_name) )

    return blk

  # Override
  def add_constraints( s, *args ):

    for (x0, x1) in args:

      # Forward total constraints to the final graph
      if isinstance( x0, U ) and isinstance( x1, U ): # Two upblks!
        s._add_expl_constraints( id(x0.func), id(x1.func) )

      # keep partial constraints for later synthesis
      else:
        x0_func = x0.func
        x1_func = x1.func

        # Store the method descriptor to instance dictionary for unique id

        if isinstance( x0, M ):
          if not x0.func.__name__  in s.__dict__:
            s.__dict__[ x0.func.__name__ ] = x0.func
          x0_func = s.__dict__[ x0.func.__name__ ]

        if isinstance( x1, M ):
          if not x1.func.__name__  in s.__dict__:
            s.__dict__[ x1.func.__name__ ] = x1.func
          x1_func = s.__dict__[ x1.func.__name__ ]

        # Partial constraints, x0 < x1
        s._predecessors[ id(x1_func) ].add( id(x0_func) )
        s._successors  [ id(x0_func) ].add( id(x1_func) )

  # Override
  def _elaborate_vars( s ):
    super( MethodComponent, s )._elaborate_vars()

    # First check and bind update blocks that calls the method to it

    method_blks = defaultdict(set)

    for blk_id, method_calls in s._blkid_methods.iteritems():
      for (object_name, method_name) in method_calls:
        obj = s
        for field in object_name:
          assert hasattr( obj, field ), "\"%s\", in %s, is not a field of class %s" \
                 %(field, s._blkid_upblk[blk_id].__name__, type(obj).__name__)
          obj = getattr( obj, field )

        assert hasattr( obj, method_name ), "\"%s\", in %s, is not a method of class %s" \
               %(method_name, s._blkid_upblk[blk_id].__name__, type(obj).__name__)
        method = getattr( obj, method_name )
        assert callable( method ), "\"%s\" is not callable %s"%(method_name, type(obj).__name__)

        # print " - ", object_name,method_name,"()", hex(id(method)), "in", s._blkid_upblk[blk_id].__name__
        method_blks[ id(method) ].add( blk_id )

    # Turn associated sets into lists, as blk_id are now unique.
    # O(logn) -> O(1)

    for i in method_blks:
      s._method_blks[i].extend( list( method_blks[i] ) )

  def _synthesize_partial_constraints( s ):

    # Do bfs to find out all potential total constraints associated with
    # each method, direction conflicts, and incomplete constraints
    #
    # upX=methodA < methodB=upY ---> upX < upY
    # upX=methodA < upY         ---> upX < upY

    # Turn associated sets into lists, as blk_id are now unique.
    # O(logn) -> O(1)
    # Then append variables called at the current level to the big dict

    # We only find constraints for upblks at the current level. However,
    # there might be some constraints in grandchild or deeper submodels.
    # So, we append these to  all previous method_blks

    method_blks = s._method_blks

    for method_id in method_blks:
      assoc_blks = method_blks[ method_id ]

      Q = deque( [ (method_id, 0) ] ) # -1: pred, 0: don't know, 1: succ
      while Q:
        (u, w) = Q.popleft()

        if w <= 0:
          for v in s._predecessors[u]:
            if v in s._blkid_upblk:
              # find total constraint (upY < upX) by upY < methodA=upX
              for blk in assoc_blks:
                assert v != blk, "Self loop at %s" % s._blkid_upblk[v].__name__
                s._expl_constraints.add( (v, blk) )

            elif v in method_blks:
              # assert v in method_blks, "Incomplete elaboration, something is wrong! %s" % hex(v)
              # TODO Now I'm leaving incomplete dependency chain because I didn't close the circuit loop.
              # E.g. I do port.wr() somewhere in __main__ to write to a port.

              # find total constraint (upY < upX) by upY=methodB < methodA=upX
              v_blks = method_blks[ v ]
              for vb in v_blks:
                for blk in assoc_blks:
                  assert vb != blk, "Self loop at %s" % s._blkid_upblk[vb].__name__
                  s._expl_constraints.add( (vb, blk) )

              Q.append( (v, -1) ) # ? < v < u < ... < method < blk_id

        if w >= 0:
          for v in s._successors[u]:
            if v in s._blkid_upblk:
              # find total constraint (upX < upY) by upX=methodA < upY
              for blk in assoc_blks:
                assert v != blk, "Self loop at %s" % s._blkid_upblk[v].__name__
                s._expl_constraints.add( (blk, v) )
            elif v in method_blks:
              # assert v in method_blks, "Incomplete elaboration, something is wrong! %s" % hex(v)
              # TODO Now I'm leaving incomplete dependency chain because I didn't close the circuit loop.
              # E.g. I do port.wr() somewhere in __main__ to write to a port.

              # find total constraint (upX < upY) by upX=methodA < methodB=upY
              v_blks = method_blks[ v ]
              for vb in v_blks:
                for blk in assoc_blks:
                  assert vb != blk, "Self loop at %s" % s._blkid_upblk[vb].__name__
                  s._expl_constraints.add( (blk, vb) )

              Q.append( (v, 1) ) # blk_id < method < ... < u < v < ?

  # Override
  def _collect_child_vars( s, child ):
    super( MethodComponent, s )._collect_child_vars( child )

    if isinstance( child, MethodComponent ):
      for k in child._predecessors:
        s._predecessors[k].update( child._predecessors[k] )
      for k in child._successors:
        s._successors[k].update( child._successors[k] )
      for k in child._method_blks:
        s._method_blks[k].extend( child._method_blks[k] )

  # Override
  def _synthesize_constraints( s ):
    super( MethodComponent, s )._synthesize_constraints()
    s._synthesize_partial_constraints()
