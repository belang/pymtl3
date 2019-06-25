#=========================================================================
# BehavioralRTLIRImplGen.py
#=========================================================================
# Author : Peitian Pan
# Date   : Jan 2, 2019
"""Generate behavioral RTLIR implementation.

This file generates (1) the implementation of the BehavioralRTLIR ASDL
defined in BehavioralRTLIR.asdl which should reside in the same
directory as this file and (2) the implementation of BehavioralRTLIR
visualization pass. The generated implementation is printed to
BehavioralRTLIR.py under the same directory. BehavioralRTLIR
visualization pass is printed to BehavioralRTLIRVisualizationPass.py
under the same directory.
"""

class constructor:
  """Class of constructors that create the behavioral RTLIR AST node types."""

  impl_template = \
"""
class {constr_name}( BaseBehavioralRTLIR ):
  {init}{eq_m}
"""

  viz_impl_template = \
"""
  def visit_{constr_name}( s, node ):
    s.cur += 1
    local_cur = s.cur
    table_body = '{table_body}'
    table_opt = s.gen_table_opt( node )
    label = (s.table_header + table_body + table_opt + s.table_trail){label_trail}
    {body}
"""

  rast_header_str = \
"""\
#=========================================================================
# BehavioralRTLIR.py
#=========================================================================
{}
""".format( '"""'+ 'Provide behavioral RTLIR AST node types.\n\n\
This file is automatically generated by BehavioralRTLIRImplGen.py.' + '\n"""' )

  rast_base_def_str = \
"""
class BaseBehavioralRTLIR( object ):
  {base_rtlir_doc}
  def __eq__( s, other ):
    return type(s) is type(other)

  def __ne__( s, other ):
    return not s.__eq__( other )
""".format( base_rtlir_doc = '"""Base class for all behavioral RTLIR AST nodes."""' )

  rast_visitor_str = \
"""
class BehavioralRTLIRNodeVisitor( object ):
  {visitor_doc}
  def visit( self, node, *args ):
    method = 'visit_' + node.__class__.__name__
    visitor = getattr( self, method, self.generic_visit )
    return visitor( node, *args )

  def generic_visit( self, node, *args ):
    for field, value in vars(node).iteritems():
      if isinstance( value, list ):
        for item in value:
          if isinstance( item, BaseBehavioralRTLIR ):
            self.visit( item, *args )
      elif isinstance( value, BaseBehavioralRTLIR ):
        self.visit( value, *args )
""".format( visitor_doc = '"""Class for behavioral RTLIR AST visitors."""' )

  viz_header_str = \
"""\
#=========================================================================
# BehavioralRTLIRVisualizationPass.py
#=========================================================================
{}

import os

from graphviz import Digraph

from pymtl3.passes.BasePass import BasePass

from pymtl3.passes.rtlir.rtype.RTLIRType import BaseRTLIRType
from .BehavioralRTLIR import BehavioralRTLIRNodeVisitor
""".format( '"""Provide visualization for behavioral RTLIR AST.\n\n\
Visualize Behavioral RTLIR using Graphviz packeage. The output graph is in PDF\n\
format.  This file is automatically generated by BehavioralRTLIRImplGen.py.\n\
"""' )

  viz_class_def_str = \
"""
class BehavioralRTLIRVisualizationPass( BasePass ):
  def __call__( s, model ):
    visitor = BehavioralRTLIRVisualizationVisitor()

    for blk in model.get_update_blocks():
      visitor.init( blk.__name__ )
      visitor.visit( model._pass_behavioral_rtlir_gen.rtlir_upblks[ blk ] )
      visitor.dump()

class BehavioralRTLIRVisualizationVisitor( BehavioralRTLIRNodeVisitor ):
  def __init__( s ):
    s.output = 'unamed'
    s.output_dir = 'rast-viz'
    s.table_header = '<<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0"> '
    s.table_trail = ' </TABLE>>'

  def init( s, name ):
    s.g = Digraph(
      comment = 'BehavioralRTLIR Visualization of ' + name,
      node_attr = { 'shape' : 'plaintext' }
    )
    s.blk_name = name
    s.cur = 0

  def get_str( s, obj ):
    return str(obj).replace('<', '&lt;').replace('>', '&gt;')

  def gen_table_opt( s, node ):
    ret = ''
    if isinstance( node.Type, BaseRTLIRType ):
      ret = ' <TR><TD COLSPAN="2">Type: ' + node.Type.__class__.__name__ + '</TD></TR>'
      for name, obj in vars(node.Type).iteritems():
        obj_str = s.get_str( obj )
        if not isinstance( obj, dict ):
          ret += ' <TR><TD>' + name + '</TD><TD>' + obj_str + '</TD></TR>'
        else:
          ret += ' <TR><TD>' + name + '</TD><TD>{' + obj_str + '}</TD></TR>'
    return ret

  def dump( s ):
    if not os.path.exists( s.output_dir ):
      os.makedirs( s.output_dir )
    s.g.render( s.output_dir + os.sep + s.blk_name )
"""

  def __init__( s, name, type_list, field_list ):
    """Entry point to initialize one type of AST node.

    `name` is the name of this constructor and should be capitalized.
    `type_list` is the list of node types of all parameters. `field_list` is
    the list of names of all parameters. If the constructor does not have any
    parameters, both lists will be None."""
    assert name[0].isupper()

    isNone = ( type_list is None ) and ( field_list is None )
    isSameLen = ( not isNone ) and ( len( type_list ) == len( field_list ) )
    assert isNone or isSameLen

    s.name = name
    s.type_list = type_list
    s.field_list = field_list

  def impl_str( s ):
    """Return the implementation of this constructor as a Python class."""
    constr_name = s.name
    if s.type_list is None:
      init = ''
      single_term = ''
      not_single_term = ''
      check_equal = ''

    else:
      # Generate statements for checking sub fields
      eq = []
      single_term = ''
      not_single_term = ''
      for t, f in zip( s.type_list, s.field_list ):
        if s.is_sequence( t ):
          eq.append( 'for x, y in zip( s.{field}, other.{field} ):'.format( field = f ) )
          eq.append( '  if x != y:' )
          eq.append( '    return False' )
        else:
          single_term += ' or s.{field} != other.{field}'.format( field = f )
          not_single_term += ' and s.{field} == other.{field}'.format( field = f )

      params_name = ', ' + ', '.join( s.field_list )
      params_assign = '\n    '.join(
        ["s.{field} = {field}".format(field = x) for x in s.field_list]
      )
      check_equal = '\n    '.join( eq )
      if check_equal:
        check_equal += '\n    '
      init = """\
def __init__( s{params_name} ):
    {params_assign}

  """.format( **locals() )

    eq_template = """\
if not isinstance(other, {constr_name}){single_term}:
      return False
    {check_equal}return True"""
    if check_equal == '':
      eq = 'return isinstance(other, {constr_name}){not_single_term}'.format( **locals() )
    else:
      eq = eq_template.format( **locals() )

    if check_equal == '' and not_single_term == '':
      if init == '':
        eq_m = 'pass'
      else:
        eq_m = ''
    else:
      eq_m = """\
def __eq__( s, other ):
    {eq}""".format( **locals() )

    return constructor.impl_template.format(
      constr_name = s.name,
      init = init,
      eq_m = eq_m
    )

  def viz_impl_str( s ):
    """Return the implementation of the visualization visitor of this
    constructor as a Python function."""
    body = []
    if s.type_list is None:
      # No parameter for this BehavioralRTLIR node.
      # Just creating a single vertex is enough.
      body.append( "s.g.node( str( s.cur ), label = label )" )
      table_body = '<TR><TD COLSPAN="2">{name}</TD></TR>'.format( name = s.name )
      body_str = '\n    '.join( body )
      body_str = body_str
      label_trail = ''

    else:
      # 1. Create a vertex corresponding to this BehavioralRTLIR node
      # 2. Add edges between this BehavioralRTLIR node and all child nodes
      body.append( "s.g.node( str( s.cur ), label = label )" )
      # The top string of vertex label
      table_body = '<TR><TD COLSPAN="2">{name}</TD></TR>'.format( name = s.name )
      # Templates for built-in fields
      built_in_str = \
        '<TR><TD>{type_name}</TD><TD>{{{value}}}</TD></TR>'
      built_in_trail = \
        '.format({built_in_trail_body})'
      built_in_trail_body = []
      # Template for user-defined fields
      customized_str = \
      "s.g.edge( str({s}), str({t}), label = '{edge_label}'{edge_label_trail} )"

      # Process each field of this BehavioralRTLIR node
      for t, f in zip( s.type_list, s.field_list ):
        if s.is_built_in( t ):
          # Add this built-in type to the label string
          # Assume built-in types will never have sequence modifier
          built_in = built_in_str.format( type_name = f, value = f )
          built_in_trail_body.append( f + '=s.get_str(node.' + f + ")" )
          table_body += ' ' + built_in
        else:
          # Add the user-defined field to the label string
          if s.is_sequence( t ):
            # A sequence of customized types
            indented = []
            indented.append('for i, f in enumerate(node.{field}):'.format(field = f))
            indented.append( customized_str.format(
              s = 'local_cur',
              t = 's.cur+1',
              edge_label = f + '[{idx}]',
              edge_label_trail = '.format(idx = i)'
            ) )
            indented.append( 's.visit( f )' )
            indented = [indented[0]] + ['  '+x for x in indented[1:]]
            body = body + indented
          else:
            # A single customized type
            body.append( customized_str.format(
              s = 'local_cur',
              t = 's.cur+1',
              edge_label = f,
              edge_label_trail = ''
            ) )
            body.append( 's.visit( node.{field} )'.format( field = f ) )
      if built_in_trail_body == []:
        label_trail = ''
      else:
        label_trail = built_in_trail.format(
          built_in_trail_body = ', '.join( built_in_trail_body ) )
      body_str = '\n    '.join( body )

    return constructor.viz_impl_template.format(
      constr_name = s.name,
      table_body = table_body,
      label_trail = label_trail,
      body = body_str
    )

  def is_built_in( s, type_name ):
    return type_name in [ 'identifier', 'int', 'object', 'bool', 'string' ]

  def is_sequence( s, type_name ):
    return type_name[-1] == '*'

  def __eq__( s, other ):
    return isinstance(other, constructor) and s.name == other.name

  def __ne__( s, other ):
    return not s.__eq__( other )

def parse_constructor( constr_str ):
  """Return the constructor object corresponding to the given string."""
  if constr_str.find( '(' ) != -1:
    # has parameters
    bracket_idx = constr_str.index( '(' )
    bracket_end_idx = constr_str.index( ')' )
    constr_name = constr_str[ 0 : bracket_idx ]
    params = constr_str[ bracket_idx + 1 : bracket_end_idx ].strip()
    params = params.split( ',' )
    type_list = []
    field_list = []
    for param in params:
      param_lst = param.strip().split()
      type_list.append( param_lst[0] )
      field_list.append( param_lst[1] )
  else:
    # no parameters
    constr_name = constr_str
    type_list = None
    field_list = None

  return constructor( constr_name, type_list, field_list )

def get_type( type_name ):
  """Return the type of the given node type string (without *? modifier)."""
  if type_name[ -1 ] == '*' or type_name[ -1 ] == '?':
    return type_name[ : -1 ]
  return type_name

def get_constr( module_str, start, end ):
  """Extract and return the constructor string from module_str[start:end];
  also return the first position past the constructor string."""
  constr_start = start
  # Remove leading spaces
  while module_str[ constr_start ] == ' ':
    constr_start += 1

  if module_str.find( '(', start, end ) != -1:
    # this constructor has parameters
    bracket_idx = module_str.find( ')', start, end )
    constr = module_str[ constr_start : bracket_idx+1 ]
    l = bracket_idx + 1
  else:
    # this constructor has no parameters
    l = constr_start
    while l < end and module_str[ l ] != ' ':
      l += 1
    constr = module_str[ constr_start : l ]

  return constr, l

def implement_module( module_str ):
  """Return a string that implements all constructors in the given module
  string."""
  start = 0
  node_type = set()
  built_in_node_type = { 'identifier', 'int', 'string', 'bool', 'object' }
  constr_list = []
  # constr_list = set()

  impl_str = constructor.rast_header_str + constructor.rast_base_def_str
  viz_impl_str = constructor.viz_header_str + constructor.viz_class_def_str

  # parse one node type at a time
  while module_str.find( '=', start ) != -1:
    assign_idx = module_str.find( '=', start )
    node_type_name = module_str[ start : assign_idx ].strip()
    node_type.add( node_type_name )

    # find the boundary of this node type
    boundary = module_str.find( '=', assign_idx + 1 )
    if boundary == -1:
      boundary = len( module_str )

    constructor_start = assign_idx + 1
    # check if there are multiple constructors
    while module_str.find( '|', constructor_start ) != -1:
      constructor_end = module_str.find( '|', constructor_start )
      if constructor_end >= boundary: break

      # parse each possible constructor and move to the next
      constr_str, l = get_constr(
        module_str, constructor_start, constructor_end
      )

      constr = parse_constructor( constr_str )

      if not constr in constr_list:
        constr_list.append( constr )
      else:
        raise Exception( 'duplicated constructor!' )
      # constr_list.add( parse_constructor( constr_str ) )

      constructor_start = constructor_end + 1

    # one constructor remaining
    constr_str, l = get_constr( module_str, constructor_start, boundary )
    constr = parse_constructor( constr_str )
    if not constr in constr_list:
      constr_list.append( constr )
    else:
      raise Exception( 'duplicated constructor!' )
    # constr_list.add( parse_constructor( constr_str ) )

    start = l

  # sanity check
  for constr in constr_list:
    if not constr.type_list is None:
      for constr_type in constr.type_list:
        assert get_type( constr_type ) in node_type.union( built_in_node_type )

  # generate implementation
  for constr in constr_list:
    impl_str += constr.impl_str()
    viz_impl_str += constr.viz_impl_str()

  impl_str += constructor.rast_visitor_str

  with open( 'BehavioralRTLIR.py', 'w' ) as output:
    output.write( impl_str )

  with open( 'BehavioralRTLIRVisualizationPass.py', 'w' ) as output:
    output.write( viz_impl_str )

def extract_module( asdl_str ):
  """Return the module name and the module string of the given asdl
  string."""
  module_name_start = asdl_str.index( 'module' ) + len( 'module' )
  module_name_end = asdl_str.index( '{' )
  module_str_end = asdl_str.index( '}' )

  module_name = asdl_str[ module_name_start : module_name_end ].strip()
  module_str  = asdl_str[ module_name_end + 1 : module_str_end ].strip()

  return module_name, module_str

# This file should be run first to generate the correct implementation
# of BehavioralRTLIR.
if __name__ == '__main__':
  with open( 'BehavioralRTLIR.asdl', 'r') as asdl_file:
    asdl_str = ''
    for line in asdl_file:
      if line.strip().startswith( '--' ) or ( not line.strip() ):
        continue
      asdl_str += line.strip() + ' '

    # BehavioralRTLIR module is the first one in the file
    module_name, module_str = extract_module( asdl_str )
    assert module_name == 'BehavioralRTLIR'

    implement_module( module_str )
