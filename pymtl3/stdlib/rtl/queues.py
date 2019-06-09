"""
-------------------------------------------------------------------------
Library of RTL queues
-------------------------------------------------------------------------

Author : Yanghui Ou
  Date : Mar 23, 2019
"""

from __future__ import absolute_import, division, print_function

from pymtl3 import *
from pymtl3.stdlib.ifcs import DeqIfcRTL, EnqIfcRTL
from pymtl3.stdlib.rtl import Mux, RegisterFile

#-------------------------------------------------------------------------
# Dpath and Ctrl for NormalQueueRTL
#-------------------------------------------------------------------------

class NormalQueueDpathRTL( Component ):

  def construct( s, MsgType, num_entries=2 ):

    # Interface

    s.enq_msg =  InPort( MsgType )
    s.deq_msg = OutPort( MsgType )

    s.wen   = InPort( Bits1 )
    s.waddr = InPort( mk_bits( clog2( num_entries ) ) )
    s.raddr = InPort( mk_bits( clog2( num_entries ) ) )

    # Component

    s.queue = RegisterFile( MsgType, num_entries )(
      raddr = { 0: s.raddr   },
      rdata = { 0: s.deq_msg },
      wen   = { 0: s.wen     },
      waddr = { 0: s.waddr   },
      wdata = { 0: s.enq_msg },
    )

class NormalQueueCtrlRTL( Component ):

  def construct( s, num_entries=2 ):

    # Constants

    s.num_entries = num_entries
    s.last_idx    = num_entries - 1
    addr_nbits    = clog2( num_entries   )
    count_nbits   = clog2( num_entries+1 )
    PtrType       = mk_bits( addr_nbits  )
    CountType     = mk_bits( count_nbits )

    # Interface

    s.enq_en  = InPort ( Bits1   )
    s.enq_rdy = OutPort( Bits1   )
    s.deq_en  = InPort ( Bits1   )
    s.deq_rdy = OutPort( Bits1   )
    s.count   = OutPort( PtrType )

    s.wen     = OutPort( Bits1   )
    s.waddr   = OutPort( PtrType )
    s.raddr   = OutPort( PtrType )

    # Registers

    s.head = Wire( PtrType )
    s.tail = Wire( PtrType )

    # Wires

    s.enq_xfer  = Wire( Bits1   )
    s.deq_xfer  = Wire( Bits1   )
    s.head_next = Wire( PtrType )
    s.tail_next = Wire( PtrType )

    # Connections

    s.connect( s.wen,   s.enq_xfer )
    s.connect( s.waddr, s.tail     )
    s.connect( s.raddr, s.head     )

    @s.update
    def up_rdy_signals():
      if ~s.reset:
        s.enq_rdy = b1(1) if s.count < s.num_entries else b1(0)
        s.deq_rdy = b1(1) if s.count > 0 else b1(0)
      else:
        s.enq_rdy = b1(0)
        s.deq_rdy = b1(0)

    @s.update
    def up_xfer_signals():
      s.enq_xfer = s.enq_en and s.enq_rdy
      s.deq_xfer = s.deq_en and s.deq_rdy

    @s.update
    def up_next():
      s.head_next = s.head - 1 if s.head > 0 else PtrType( s.last_idx )
      s.tail_next = s.tail + 1 if s.tail < s.last_idx else PtrType(0)

    @s.update_on_edge
    def up_reg():

      if s.reset:
        s.head  = PtrType(0)
        s.tail  = PtrType(0)
        s.count = CountType(0)

      else:
        s.head  = s.head_next if s.deq_xfer else s.head
        s.tail  = s.tail_next if s.enq_xfer else s.tail
        s.count = s.count + b1(1) if s.enq_xfer and not s.deq_xfer else \
                  s.count - b1(1) if s.deq_xfer and not s.enq_xfer else \
                  s.count

#-------------------------------------------------------------------------
# NormalQueueRTL
#-------------------------------------------------------------------------

class NormalQueueRTL( Component ):

  def construct( s, MsgType, num_entries=2 ):

    # Interface

    s.enq   = EnqIfcRTL( MsgType )
    s.deq   = DeqIfcRTL( MsgType )
    s.count = OutPort( mk_bits( clog2( num_entries ) ) )

    # Components

    s.ctrl  = NormalQueueCtrlRTL ( num_entries )
    s.dpath = NormalQueueDpathRTL( MsgType, num_entries )

    # Connect ctrl to data path

    s.connect( s.ctrl.wen,     s.dpath.wen     )
    s.connect( s.ctrl.waddr,   s.dpath.waddr   )
    s.connect( s.ctrl.raddr,   s.dpath.raddr   )

    # Connect to interface

    s.connect( s.enq.en,  s.ctrl.enq_en   )
    s.connect( s.enq.rdy, s.ctrl.enq_rdy  )
    s.connect( s.deq.en,  s.ctrl.deq_en   )
    s.connect( s.deq.rdy, s.ctrl.deq_rdy  )
    s.connect( s.count,   s.ctrl.count    )
    s.connect( s.enq.msg, s.dpath.enq_msg )
    s.connect( s.deq.msg, s.dpath.deq_msg )

  # Line trace

  def line_trace( s ):
    return "{}({}){}".format( s.enq, s.count, s.deq )

#-------------------------------------------------------------------------
# Ctrl for PipeQueue
#-------------------------------------------------------------------------

class PipeQueueCtrlRTL( Component ):

  def construct( s, num_entries=2 ):

    # Constants

    s.num_entries = num_entries
    s.last_idx    = num_entries - 1
    addr_nbits    = clog2( num_entries   )
    count_nbits   = clog2( num_entries+1 )
    PtrType       = mk_bits( addr_nbits  )
    CountType     = mk_bits( count_nbits )

    # Interface

    s.enq_en  = InPort ( Bits1   )
    s.enq_rdy = OutPort( Bits1   )
    s.deq_en  = InPort ( Bits1   )
    s.deq_rdy = OutPort( Bits1   )
    s.count   = OutPort( PtrType )

    s.wen     = OutPort( Bits1   )
    s.waddr   = OutPort( PtrType )
    s.raddr   = OutPort( PtrType )

    # Registers

    s.head = Wire( PtrType )
    s.tail = Wire( PtrType )

    # Wires

    s.enq_xfer  = Wire( Bits1   )
    s.deq_xfer  = Wire( Bits1   )
    s.head_next = Wire( PtrType )
    s.tail_next = Wire( PtrType )

    # Connections

    s.connect( s.wen,   s.enq_xfer )
    s.connect( s.waddr, s.tail     )
    s.connect( s.raddr, s.head     )

    @s.update
    def up_rdy_signals():
      if ~s.reset:
        s.deq_rdy = b1(1) if s.count > 0 else b1(0)
      else:
        s.deq_rdy = b1(0)

    @s.update
    def up_enq_rdy():
      if ~s.reset:
        s.enq_rdy = s.count < s.num_entries or s.deq_en
      else:
        s.enq_rdy = b1(0)


    @s.update
    def up_xfer_signals():
      s.enq_xfer  = s.enq_en and s.enq_rdy
      s.deq_xfer  = s.deq_en and s.deq_rdy

    @s.update
    def up_next():
      s.head_next = s.head - b1(1) if s.head > 0 else PtrType( s.last_idx )
      s.tail_next = s.tail + b1(1) if s.tail < s.last_idx else PtrType(0)

    @s.update_on_edge
    def up_reg():

      if s.reset:
        s.head  = PtrType(0)
        s.tail  = PtrType(0)
        s.count = CountType(0)

      else:
        s.head  = s.head_next if s.deq_xfer else s.head
        s.tail  = s.tail_next if s.enq_xfer else s.tail
        s.count = s.count + b1(1) if s.enq_xfer and not s.deq_xfer else \
                  s.count - b1(1) if s.deq_xfer and not s.enq_xfer else \
                  s.count

#-------------------------------------------------------------------------
# PipeQueueRTL
#-------------------------------------------------------------------------

class PipeQueueRTL( Component ):

  def construct( s, MsgType, num_entries=2 ):

    # Interface

    s.enq   = EnqIfcRTL( MsgType )
    s.deq   = DeqIfcRTL( MsgType )
    s.count = OutPort( mk_bits( clog2( num_entries ) ) )

    # Components

    s.ctrl  = PipeQueueCtrlRTL ( num_entries )
    s.dpath = NormalQueueDpathRTL( MsgType, num_entries )

    # Connect ctrl to data path

    s.connect( s.ctrl.wen,     s.dpath.wen     )
    s.connect( s.ctrl.waddr,   s.dpath.waddr   )
    s.connect( s.ctrl.raddr,   s.dpath.raddr   )

    # Connect to interface

    s.connect( s.enq.en,  s.ctrl.enq_en   )
    s.connect( s.enq.rdy, s.ctrl.enq_rdy  )
    s.connect( s.deq.en,  s.ctrl.deq_en   )
    s.connect( s.deq.rdy, s.ctrl.deq_rdy  )
    s.connect( s.count,   s.ctrl.count    )
    s.connect( s.enq.msg, s.dpath.enq_msg )
    s.connect( s.deq.msg, s.dpath.deq_msg )

  # Line trace

  def line_trace( s ):
    return "{}({}){}".format( s.enq, s.count, s.deq )

#-------------------------------------------------------------------------
# Ctrl and Dpath for BypassQueue
#-------------------------------------------------------------------------

class BypassQueueDpathRTL( Component ):

  def construct( s, MsgType, num_entries=2 ):

    # Interface

    s.enq_msg =  InPort( MsgType )
    s.deq_msg = OutPort( MsgType )

    s.wen     = InPort( Bits1 )
    s.waddr   = InPort( mk_bits( clog2( num_entries ) ) )
    s.raddr   = InPort( mk_bits( clog2( num_entries ) ) )
    s.mux_sel = InPort( Bits1 )

    # Component

    s.queue = RegisterFile( MsgType, num_entries )(
      raddr = { 0: s.raddr   },
      wen   = { 0: s.wen     },
      waddr = { 0: s.waddr   },
      wdata = { 0: s.enq_msg },
    )

    s.mux = Mux( MsgType, 2 )(
      sel = s.mux_sel,
      in_ = { 0: s.queue.rdata[0], 1: s.enq_msg },
      out = s.deq_msg,
    )

class BypassQueueCtrlRTL( Component ):

  def construct( s, num_entries=2 ):

    # Constants

    s.num_entries = num_entries
    s.last_idx    = num_entries - 1
    addr_nbits    = clog2( num_entries   )
    count_nbits   = clog2( num_entries+1 )
    PtrType       = mk_bits( addr_nbits  )
    CountType     = mk_bits( count_nbits )

    # Interface

    s.enq_en  = InPort ( Bits1   )
    s.enq_rdy = OutPort( Bits1   )
    s.deq_en  = InPort ( Bits1   )
    s.deq_rdy = OutPort( Bits1   )
    s.count   = OutPort( PtrType )

    s.wen     = OutPort( Bits1   )
    s.waddr   = OutPort( PtrType )
    s.raddr   = OutPort( PtrType )
    s.mux_sel = OutPort( Bits1   )

    # Registers

    s.head = Wire( PtrType )
    s.tail = Wire( PtrType )

    # Wires

    s.enq_xfer  = Wire( Bits1   )
    s.deq_xfer  = Wire( Bits1   )
    s.head_next = Wire( PtrType )
    s.tail_next = Wire( PtrType )

    # Connections

    s.connect( s.wen,   s.enq_xfer )
    s.connect( s.waddr, s.tail     )
    s.connect( s.raddr, s.head     )

    @s.update
    def up_enq_rdy():
      if ~s.reset:
        s.enq_rdy = b1(1) if s.count < s.num_entries else b1(0)
      else:
        s.enq_rdy = b1(0)

    @s.update
    def up_deq_rdy():
      if ~s.reset:
        s.deq_rdy = b1(1) if s.count > 0 or s.enq_en else b1(0)
      else:
        s.deq_rdy = b1(0)
    
    @s.update
    def up_mux_sel():
      s.mux_sel = b1(0) if s.count > 0 else b1(1)

    @s.update
    def up_xfer_signals():
      s.enq_xfer  = s.enq_en and s.enq_rdy
      s.deq_xfer  = s.deq_en and s.deq_rdy

    @s.update
    def up_next():
      s.head_next = s.head - 1 if s.head > 0 else PtrType( s.last_idx )
      s.tail_next = s.tail + 1 if s.tail < s.last_idx else PtrType(0)

    @s.update_on_edge
    def up_reg():

      if s.reset:
        s.head  = PtrType(0)
        s.tail  = PtrType(0)
        s.count = CountType(0)

      else:
        s.head   = s.head_next if s.deq_xfer else s.head
        s.tail   = s.tail_next if s.enq_xfer else s.tail
        s.count  = s.count + b1(1) if s.enq_xfer and not s.deq_xfer else \
                   s.count - b1(1) if s.deq_xfer and not s.enq_xfer else \
                   s.count

#-------------------------------------------------------------------------
# BypassQueueRTL
#-------------------------------------------------------------------------

class BypassQueueRTL( Component ):

  def construct( s, MsgType, num_entries=2 ):

    # Interface

    s.enq   = EnqIfcRTL( MsgType )
    s.deq   = DeqIfcRTL( MsgType )
    s.count = OutPort( mk_bits( clog2( num_entries ) ) )

    # Components

    s.ctrl  = BypassQueueCtrlRTL ( num_entries )
    s.dpath = BypassQueueDpathRTL( MsgType, num_entries )

    # Connect ctrl to data path

    s.connect( s.ctrl.wen,     s.dpath.wen     )
    s.connect( s.ctrl.waddr,   s.dpath.waddr   )
    s.connect( s.ctrl.raddr,   s.dpath.raddr   )
    s.connect( s.ctrl.mux_sel, s.dpath.mux_sel )

    # Connect to interface

    s.connect( s.enq.en,  s.ctrl.enq_en   )
    s.connect( s.enq.rdy, s.ctrl.enq_rdy  )
    s.connect( s.deq.en,  s.ctrl.deq_en   )
    s.connect( s.deq.rdy, s.ctrl.deq_rdy  )
    s.connect( s.count,   s.ctrl.count    )
    s.connect( s.enq.msg, s.dpath.enq_msg )
    s.connect( s.deq.msg, s.dpath.deq_msg )

  # Line trace

  def line_trace( s ):
    return "{}({}){}".format( s.enq, s.count, s.deq )
