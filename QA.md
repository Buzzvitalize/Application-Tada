# QA Checklist

## Visual / Manual
- [ ] Filtros permiten seleccionar rangos y el botón *Reset* limpia la vista.
- [ ] Las gráficas reaccionan dinámicamente a los filtros incluso bajo carga.
- [ ] Las tablas vacías muestran el mensaje "Sin datos" claramente.
- [ ] Exportaciones CSV/PDF/XLSX incluyen encabezados con empresa, usuario y fechas.

## Performance
- [ ] Consultas de 10k registros responden < 3s.
- [ ] Exportaciones grandes (>50k) completan en background < 10s.

## Seguridad
- [ ] Usuarios solo ven datos de su empresa (multi-tenant).
- [ ] Roles sin permiso reciben mensaje de error al exportar.

Revisar cada punto en ambiente de *staging* antes de desplegar a producción.
