import math

import glm

template mathPerComponent(op: untyped): untyped =
  # int vector and float vector
  proc op*[T: SomeFloat](v: Vec3[SomeInteger], u: Vec3[T]): Vec3[T] {.noinit.} =
    for i in 0..<3:
      result.arr[i] = op(v.arr[i].T, u.arr[i])

  proc op*[T: SomeFloat](v: Vec3[T], u: Vec3[SomeInteger]): Vec3[T] {.noinit.} =
    for i in 0..<3:
      result.arr[i] = op(v.arr[i], u.arr[i].T)

  # int vector and float value
  proc op*[T: SomeFloat](v: Vec3[SomeInteger], val: T): Vec3[T] {.noinit.} =
    for i in 0..<3:
      result.arr[i] = op(v.arr[i].T, val)

  proc op*[T: SomeFloat](val: T, v: Vec3[SomeInteger]): Vec3[T] {.noinit.} =
    for i in 0..<3:
      result.arr[i] = op(val, v.arr[i].T)

  # float vector and int value
  proc op*[T: SomeFloat](v: Vec3[T], val: SomeInteger): Vec3[T] {.noinit.} =
    for i in 0..<3:
      result.arr[i] = op(v.arr[i], val.T)

  proc op*[T: SomeFloat](val: SomeInteger, v: Vec3[T]): Vec3[T] {.noinit.} =
    for i in 0..<3:
      result.arr[i] = op(val.T, v.arr[i])


mathPerComponent(`+`)
mathPerComponent(`-`)
mathPerComponent(`/`)
mathPerComponent(`*`)
mathPerComponent(`div`)
mathPerComponent(`mod`)


template mathInpl(opName: untyped): untyped =
  proc opName*[T: SomeFloat](v: var Vec3[T], u: Vec3[SomeInteger]) =
    for i in 0..<3:
      opName(v.arr[i], u.arr[i].T)

  proc opName*[T: SomeFloat](v: var Vec3[T], val: SomeInteger) =
    for i in 0..<3:
      opName(v.arr[i], val.T)


mathInpl(`+=`)
mathInpl(`-=`)
mathInpl(`*=`)
mathInpl(`/=`)


proc floorMod*[T: SomeInteger](v: Vec3[T], val: T): Vec3[T] {.noinit.} =
  for i in 0..<3:
    result.arr[i] = v.arr[i].floorMod(val)


proc toFloat32*[T: SomeInteger](v: Vec3[T]): Vec3[float32] {.noinit.} =
  for i in 0..<3:
    result.arr[i] = v.arr[i].float32
