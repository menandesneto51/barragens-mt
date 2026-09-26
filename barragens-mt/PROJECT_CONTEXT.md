# PROJECT CONTEXT — VIGIBARRAGENS-MT

## Missão

Monitorar barragens em Mato Grosso sob perspectiva integrada de segurança, hidrometeorologia, território, exposição populacional e capacidade de resposta em saúde, apoiando CIEVS/SIS, Vigidesastres, Sala de Situação e atores responsáveis.

## Princípio territorial

A localização administrativa da barragem não define o perímetro da ameaça. O sistema deve avaliar montante/jusante, bacia, drenagem, manchas e territórios potencialmente atingidos.

## Estado atual

O produto operacional usa pipeline Python, arquivos tratados, Streamlit e produtos HTML. Possui inventário SNISB, SIGBM/ANM, IBGE, IDAP estadual, integração SisClima/TITAN, BHO/Otto, CNES, populações vulneráveis, alertabilidade, fila de alertas, Barragem 360°, piloto Manso–Cuiabá, simulações proxy e produtos operacionais.

## Direção v2

Evolução incremental para PostgreSQL/PostGIS como fonte central, séries temporais quando necessário, camada de repositórios, histórico, qualidade/lineage, detecção de mudanças, WebGIS operacional e observabilidade.

Cadeia-alvo:
SNISB/SIGBM → snapshot histórico → detecção de mudanças → IDAP → risco hidroclimático → exposição territorial → capacidade de resposta → nível operacional → alerta → confirmação → SITREP.

## Integrações

SisClima/TITAN é a fonte integrada preferencial para componentes hidrometeorológicos já coletados e validados. Não duplicar INMET, Cemaden ou ANA quando o contrato existente atender à necessidade.

## Governança de IA

IA é camada assistiva. Regras oficiais, índices, níveis e gatilhos devem permanecer determinísticos e auditáveis. Qualquer texto gerado para comunicação de risco requer rastreabilidade dos fatos utilizados e revisão humana quando destinado a publicação/despacho institucional.

## Migração

A versão atual deve permanecer funcional durante a evolução. CSV pode continuar como contrato transitório até a camada PostgreSQL/PostGIS atingir equivalência operacional e validação.
