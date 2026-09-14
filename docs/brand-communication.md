# Identidade visual e comunicação

## Objetivo

Padronizar alertas e relatórios da automação Notion/GChat de acordo com a
identidade da HIVEPlace. O Notion continua sendo a fonte oficial do histórico;
o Google Chat é um canal de orientação e coordenação.

## Posicionamento e voz

O posicionamento digital vigente é “A primeira agência de interoperabilidade do
Brasil”. A comunicação deve traduzir complexidade em ação clara, com o tom
Visionário Soberano: seguro, preciso, pragmático, elegante e sem jargão vazio.

Priorizar verbos que indiquem resultado, como orquestrar, governar, estruturar,
desbloquear, habilitar, traduzir e escalar. Todo alerta deve deixar explícitos
o fato, o responsável, a próxima ação e o link do registro.

Evitar exposição, culpa, ameaça, urgência sem evidência, excesso de emojis e
frases genéricas. A mensagem cobra a atualização do registro, não a pessoa.

## Paleta digital

| Nome | Hexadecimal | Aplicação |
| --- | --- | --- |
| Preto | `#0D0D0E` | Fundo e estrutura |
| Marrom escuro | `#332528` | Fundo institucional e seções |
| Dourado | `#EFB41B` | Destaque institucional |
| Dourado escuro | `#D98E06` | Atenção e chamada sobre fundo claro |
| Marrom | `#5D2E07` | Apoio e bloqueio |
| Marrom quase preto | `#1A1214` | Fundo escuro secundário |
| Grafite | `#1A1A1C` | Texto forte e neutros |
| Cinza | `#404146` | Texto secundário e bordas |
| Branco | `#EEF1F0` | Texto em fundo escuro e fundo claro |

O dourado é reservado para orientar o olhar. Cores semânticas de estado são
uma camada separada da identidade: vermelho para prazo vencido, marrom para
bloqueio, dourado escuro para aprovação/atualização e verde discreto para
conclusão. O status também deve ser escrito; nunca depender apenas da cor.

## Tipografia

Manrope é a referência digital preferencial por ser uma família aberta. Neue
Haas Grotesk permanece adequada para peças gráficas quando houver licença e
disponibilidade. O webhook não controla a fonte do Google Chat; a hierarquia é
obtida por título, subtítulo, negrito, cor, espaçamento e cards, sem adicionar
fonte como dependência do runtime.

## Formato dos alertas

```text
Alerta de acompanhamento — [tipo]

[quantidade] pendência(s)

- [registro]
  Responsável: [nome]
  Aprovador(es): [nome]       # obrigatório para aprovação
  Prazo: [data]
  Última atividade: [data]
  Último comentário: [autor] — [resumo]
  Ação: [próximo passo objetivo]
  Link: [Notion]
```

Regras transversais:

- tarefas em aprovação mostram o aprovador, não apenas o executor;
- todo comentário exibido mostra seu autor;
- bloqueios mostram o responsável pela ação de desbloqueio;
- ausência de informação é explícita (`não informado`);
- o link direto permanece disponível no texto e no botão do card;
- o Notion não é alterado automaticamente.

## Categorias de cards

O código utiliza categorias explícitas (`overdue`, `blocked`, `approval`,
`stale`, `management_report` e `general`) para aplicar cor semântica. A
categoria não deve ser inferida pela cor do texto nem exigir conhecimento de
hexadecimais na lógica de negócio.

## Checklist de revisão

- A mensagem informa o que ocorreu e a ação esperada?
- Responsável, aprovador e autor estão presentes quando aplicável?
- O texto é objetivo, respeitoso e orientado a resultado?
- O destaque dourado está sendo usado com parcimônia?
- O status aparece por texto além da cor?
- O link abre diretamente a página oficial no Notion?
- O fallback textual continua completo?
