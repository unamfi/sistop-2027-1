#!/usr/bin/ruby
require 'concurrent'

$s1 = Concurrent::Semaphore.new(0)
$s2 = Concurrent::Semaphore.new(0)

class EjemploHilos
  def initialize
    @x = 0
  end
  def f1
    sleep 0.1
    $s1.acquire
    print '+'
    @x += 3
    $s2.release
  end
  def f2
    sleep 0.1
    print '*'
    @x *= 2
    $s1.release
  end
  def run
    t1 = Thread.new {f1}
    t2 = Thread.new {f2}
    sleep 0.1
    $s2.acquire
    print '%d ' % @x
  end
end

e = EjemploHilos.new
10.times { e.run }
