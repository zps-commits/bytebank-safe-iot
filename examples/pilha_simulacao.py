"""Demonstra no computador a mesma lógica LIFO (sem ESP32)."""
pendentes = []
pendentes.append('envelope-A')
pendentes.append('envelope-B')
print('PUSH A, PUSH B:', pendentes)
ultimo = pendentes.pop()
print('POP (cancelamento):', ultimo)
print('Restante para confirmar:', pendentes)
assert ultimo == 'envelope-B'
assert pendentes == ['envelope-A']
