#=========================================================================
# SVTranslator.py
#=========================================================================
# Author : Peitian Pan
# Date   : March 15, 2019
"""Provide SystemVerilog translator."""

from pymtl3.passes.translator import RTLIRTranslator

from .behavioral import SVBehavioralTranslator as SV_BTranslator
from .structural import SVStructuralTranslator as SV_STranslator

sverilog_keyword = [
  # Verilog-1995 reserved keywords
  "always", "and", "assign", "begin", "buf", "bufif0", "bufif1", "case",
  "casex", "casez", "cmos", "deassign", "default", "defparam", "disable",
  "edge", "else", "end", "endcase", "endmodule", "endfunction", "endprimitive",
  "endspecify", "endtable", "endtask", "event", "for", "force", "forever",
  "fork", "function", "highz0", "highz1", "if", "ifnone", "initial",
  "inout", "input", "output", "integer", "join", "large", "macromodule",
  "medium", "module", "nand", "negedge", "nmos", "nor", "not", "notif0",
  "notif1", "or", "output", "parameter", "pmos", "posedge", "primitive",
  "pull0", "pull1", "pullup", "pulldown", "rcmos", "real", "realtime",
  "reg", "release", "repeat", "rnmos", "rpmos", "rtran", "rtranif0",
  "rtranif1", "scalared", "small", "specify", "specparam", "strong0",
  "strong1", "supply0", "supply1", "table", "task", "time", "tran",
  "tranif0", "tranif1", "tri", "tri0", "tri1", "triand", "trior",
  "trireg", "vectored", "wait", "wand", "weak0", "weak1", "while",
  "wire", "wor", "xnor", "xor",
  # Verilog-2001 reserved keywords
  "automatic", "cell", "config", "design", "endconfig", "endgenerate",
  "generate", "genvar", "incdir", "include", "instance", "liblist",
  "library", "localparam", "noshowcancelled", "pulsestyle_onevent",
  "pulsestyle_ondetect", "showcancelled", "signed", "unsigned", "use",
  # Verilog-2005 reserved keywords
  "uwire",
  # SystemVerilog-2005 reserved keywords
  "alias", "always_comb", "always_ff", "always_latch", "assert", "assume",
  "before", "bind", "bins", "binsof", "bit", "break", "byte", "chandle",
  "class", "clocking", "const", "constraint", "context", "continue",
  "cover", "covergroup", "coverpoint", "cross", "dist", "do", "endclass",
  "endclocking", "endgroup", "endinterface", "endpackage", "endprimitive",
  "endprogram", "endproperty", "endsequence", "enum", "expect", "export",
  "extends", "extern", "final", "first_match", "foreach", "forkjoin",
  "iff", "ignore_bins", "illegal_bins", "import", "inside", "int", "interface",
  "intersect", "join_any", "join_none", "local", "logic", "longint", "matches",
  "modport", "new", "null", "package", "packed", "priority", "program",
  "property", "protected", "pure", "rand", "randc", "randcase", "randsequence",
  "ref", "return", "sequence", "shortint", "shortreal", "solve", "static",
  "string", "struct", "super", "tagged", "this", "throughout", "timeprecision",
  "timeunit", "type", "typedef", "union", "unique", "var", "virtual", "void",
  "wait_order", "wildcard", "with", "within"
]
sverilog_reserved = set( sverilog_keyword )

def mk_SVTranslator( _RTLIRTranslator, _STranslator, _BTranslator ):

  class _SVTranslator( _RTLIRTranslator, _STranslator, _BTranslator ):

    def get_pretty( s, namespace, attr, newline=True ):
      ret = getattr(namespace, attr, "")
      if newline and (ret and ret[-1] != '\n'):
        ret += "\n"
      return ret

    def is_sverilog_reserved( s, name ):
      return name in sverilog_reserved

    def set_header( s ):
      s.header = \
"""\
//-------------------------------------------------------------------------
// {name}.sv
//-------------------------------------------------------------------------
// This file is generated by PyMTL SystemVerilog translation pass.

"""

    def rtlir_tr_src_layout( s, hierarchy ):
      s.set_header()
      name = s._top_module_full_name
      ret = s.header.format( **locals() )

      # Add struct definitions
      for struct_dtype, tplt in hierarchy.decl_type_struct:
        template = \
"""\
// Definition of PyMTL BitStruct {dtype_name}
// {file_info}
{struct_def}\
"""
        dtype_name = struct_dtype.get_name()
        file_info = struct_dtype.get_file_info()
        struct_def = tplt['def'] + '\n'
        ret += template.format( **locals() )

      # Add component sources
      ret += hierarchy.component_src
      return ret

    def rtlir_tr_components( s, components ):
      return "\n\n".join( components )

    def rtlir_tr_component( s, behavioral, structural ):

      template =\
"""\
// Definition of PyMTL Component {component_name}
// {file_info}
module {module_name}
(
{ports});
{body}
endmodule
"""
      component_name = getattr( structural, "component_name" )
      file_info = getattr( structural, "component_file_info" )
      ports_template = "{port_decls}{ifc_decls}"
      module_name = getattr( structural, "component_unique_name" )

      port_decls = s.get_pretty(structural, 'decl_ports', False)
      ifc_decls = s.get_pretty(structural, 'decl_ifcs', False)
      if port_decls or ifc_decls:
        if port_decls and ifc_decls:
          port_decls += ',\n'
        ifc_decls += '\n'
      ports = ports_template.format(**locals())

      const_decls = s.get_pretty(structural, "decl_consts")
      fvar_decls = s.get_pretty(behavioral, "decl_freevars")
      wire_decls = s.get_pretty(structural, "decl_wires")
      tmpvar_decls = s.get_pretty(behavioral, "decl_tmpvars")
      subcomp_decls = s.get_pretty(structural, "decl_subcomps")
      upblk_decls = s.get_pretty(behavioral, "upblk_decls")
      body = const_decls + fvar_decls + wire_decls + subcomp_decls \
           + tmpvar_decls + upblk_decls
      connections = s.get_pretty(structural, "connections")
      if (body and connections) or (not body and connections):
        connections = '\n' + connections
      body += connections

      s._top_module_name = getattr( structural, "component_name", module_name )
      s._top_module_full_name = module_name
      return template.format( **locals() )

  return _SVTranslator

SVTranslator = mk_SVTranslator( RTLIRTranslator, SV_STranslator, SV_BTranslator )
