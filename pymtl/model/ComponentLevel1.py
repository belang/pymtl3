#=========================================================================
# ComponentLevel1.py
#=========================================================================
# At the bottom level, we only have update blocks and explicit constraints
# between two update blocks/one update block. Basically this layer defines
# the scheduling policy/elaboration process.
# Each update block is called exactly once every cycle. PyMTL will
# schedule all update blocks based on the constraints. A total constraint
# between two update blocks specifies the order of the two blocks, i.e.
# call A before B.
# We collect one type of explicit constraints at this level:
# * Block constraint: s.add_constraints( U(upA) < U(upB) )

from NamedObject     import NamedObject
from ConstraintTypes import U
from errors          import UpblkFuncSameNameError, NotElaboratedError
from pymtl.datatypes import *

import inspect2, re, ast, py
p = re.compile('( *((@|def).*))')

class ComponentLevel1( NamedObject ):

  #-----------------------------------------------------------------------
  # Private methods
  #-----------------------------------------------------------------------

  def __new__( cls, *args, **kwargs ):
    """ Convention: variables local to the object is created in __new__ """

    inst = super( ComponentLevel1, cls ).__new__( cls, *args, **kwargs )

    inst._name_upblk = {}
    inst._upblks     = set()
    inst._U_U_constraints = set() # contains ( id(func), id(func) )s

    return inst

  def _declare_vars( s ):
    """ Convention: the top level component on which we call elaborate
    declare variables in _declare_vars; it shouldn't have them before
    elaboration.

    Convention: the variables that hold all metadata of descendants
    should have _all prefix."""

    s._all_upblks = set()
    s._all_upblk_hostobj = {}
    s._all_U_U_constraints = set()

  def _collect_vars( s, m ):
    """ Called on individual objects during elaboration.
    The general format resembles "s._all_X.update/append( s._X ). """

    if isinstance( m, ComponentLevel1 ):
      s._all_upblks |= m._upblks
      s._all_upblk_hostobj.update( { blk: m for blk in m._upblks } )
      s._all_U_U_constraints |= m._U_U_constraints

  def _uncollect_vars( s, m ):

    if isinstance( m, ComponentLevel1 ):
      s._all_upblks -= m._upblks
      s._all_upblk_hostobj = { k:v for k,v in s._all_upblk_hostobj.iteritems()
                               if k not in m._upblks }
      s._all_U_U_constraints -= m._U_U_constraints

  #-----------------------------------------------------------------------
  # Construction-time APIs
  #-----------------------------------------------------------------------

  def update( s, blk ):
    name = blk.__name__
    if name in s._name_upblk:
      raise UpblkFuncSameNameError( name )

    s._name_upblk[ name ] = blk
    s._upblks.add( blk )
    return blk

  def add_constraints( s, *args ):
    for (x0, x1) in args:
      assert isinstance( x0, U ) and isinstance( x1, U ), "Only accept up1<up2"
      assert (x0.func, x1.func) not in s._U_U_constraints, \
        "Duplicated constraint"
      s._U_U_constraints.add( (x0.func, x1.func) )

  #-----------------------------------------------------------------------
  # elaborate
  #-----------------------------------------------------------------------

  def elaborate( s ):
    if s._constructed:
      return
    NamedObject.elaborate( s )

    s._declare_vars()
    s._all_components = s._recursive_collect( lambda x: isinstance( x, ComponentLevel1 ) )
    for c in s._all_components:
      c._elaborate_top = s
      s._collect_vars( c )

  def construct( s, *args, **kwargs ):
    raise NotImplementedError("construct method, where the design is built,"
                              " is not implemented in {}".format( s.__class__.__name__ ) )

  #-----------------------------------------------------------------------
  # Public APIs (only can be called after elaboration)
  #-----------------------------------------------------------------------

  def is_component( s ):
    return True

  def is_signal( s ):
    return False

  def is_interface( s ):
    return False

  def get_update_block( s, name ):
    return s._name_upblk[ name ]

  def get_all_update_blocks( s ):
    try:
      return s._all_upblks
    except AttributeError:
      raise NotElaboratedError()

  def get_component_level( s ):
    try:
      return len( s._full_name_idx[0] )
    except AttributeError:
      raise NotElaboratedError()

  def get_all_explicit_constraints( s ):
    return s._all_U_U_constraints

  def get_all_components( s ):
    return s._recursive_collect( lambda x: isinstance( x, ComponentLevel1 ) )

  def delete_component_by_name( s, name ):

    # This nested delete function is to create an extra layer to properly
    # call garbage collector. If we can make sure it is collected
    # automatically and fast enough, we might remove this extra layer
    #
    # EDIT: After experimented w/ and w/o gc.collect(), it seems like it
    # is eventually collected, but sometimes the intermediate memory
    # footprint might reach up to gigabytes, so let's keep the
    # gc.collect() for now

    def _delete_component_by_name( parent, name ):
      obj = getattr( parent, name )
      top = s._elaborate_top

      # Remove all components and uncollect metadata

      removed_components = obj.get_all_components()
      top._all_components -= removed_components

      for x in removed_components:
        assert x._elaborate_top is top
        top._uncollect_vars( x )

      for x in obj._recursive_collect():
        del x._parent_obj

      delattr( s, name )

    _delete_component_by_name( s, name )
    import gc
    gc.collect()

  def add_component_by_name( s, name, obj ):
    assert not hasattr( s, name )
    NamedObject.__setattr__ = NamedObject.__setattr_for_elaborate__
    setattr( s, name, obj )
    del NamedObject.__setattr__

    top = s._elaborate_top

    added_components = obj.get_all_components()
    top._all_components |= added_components

    for c in added_components:
      c._elaborate_top = top
      top._collect_vars( c )
