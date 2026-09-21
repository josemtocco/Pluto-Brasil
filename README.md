# Pluto TV Brasil → M3U para SS IPTV

Gerador automático de uma playlist M3U usando a API pública da Pluto TV.

## Como usar

1. Crie um repositório público no GitHub.
2. Envie:
   - `gerar_lista.py`
   - `pluto-brasil.m3u`
   - `.github/workflows/atualizar.yml`
   - `README.md`
3. Execute o workflow **Atualizar Pluto TV Brasil** uma vez em:
   **Actions → Atualizar Pluto TV Brasil → Run workflow**.
4. Depois, no SS IPTV, use:

```text
https://raw.githubusercontent.com/SEU_USUARIO/SEU_REPOSITORIO/main/pluto-brasil.m3u
```

## Atualização automática

O GitHub Actions executa o gerador a cada 6 horas e substitui a playlist.

## Observação importante

As URLs HLS da Pluto TV são autenticadas/tokenizadas e podem expirar. Por isso o arquivo M3U precisa ser regenerado periodicamente; não é recomendável manter URLs de sessão copiadas manualmente.

O projeto utiliza somente os canais disponibilizados pela Pluto TV para a região configurada no gerador.
