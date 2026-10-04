"""
Banco de temas do canal.

Cada tema tem um "angulo" (o recorte que o roteirista deve seguir, sempre pelo
lado sombrio/misterioso) e "queries" de reserva para buscar arte de dominio
publico no Wikimedia Commons quando o LLM nao devolver boas queries.

O campo "titulo" aparece NA TELA como headline do video — por isso ele leva
acentuacao correta. Com ~48 temas e 1 video/dia, voce tem mais de um mes de
conteudo sem repetir. Adicione novos itens no mesmo formato.
"""

TOPICS = [
    # ---------------- Personagens populares (prioridade editorial) ----------------
    {"id": "zeus", "titulo": "Zeus", "popular": 100, "angulo": "ele não era originalmente o deus mais poderoso: precisou derrubar o próprio pai para chegar ao trono"},
    {"id": "medusa-pop", "titulo": "Medusa", "popular": 99, "angulo": "Medusa nem sempre foi um monstro: a maldição veio depois de um encontro com Poseidon"},
    {"id": "hades-pop", "titulo": "Hades", "popular": 98, "angulo": "Hades não era o diabo grego: ele governava um reino que quase ninguém conseguia deixar"},
    {"id": "afrodite", "titulo": "Afrodite", "popular": 97, "angulo": "a deusa do amor nasceu de uma violência no mar e chegou à praia já adulta"},
    {"id": "thor", "titulo": "Thor", "popular": 96, "angulo": "o martelo de Thor tinha um cabo curto por causa de um erro durante a forja"},
    {"id": "loki", "titulo": "Loki", "popular": 95, "angulo": "o deus da trapaça era capaz de mudar de forma e chegou a dar à luz"},
    {"id": "odin", "titulo": "Odin", "popular": 94, "angulo": "Odin sacrificou um olho para beber da fonte que guardava todo o conhecimento"},
    {"id": "hercules", "titulo": "Hércules", "popular": 93, "angulo": "os doze trabalhos foram uma punição por um crime cometido durante uma loucura divina"},
    {"id": "aquiles", "titulo": "Aquiles", "popular": 92, "angulo": "Aquiles não era totalmente invulnerável e sua famosa fraqueza não aparece como muitos imaginam"},
    {"id": "anubis-pop", "titulo": "Anúbis", "popular": 91, "angulo": "Anúbis não era o deus da morte: ele guiava os mortos e pesava seus corações"},
    {"id": "iara-pop", "titulo": "Iara", "popular": 90, "angulo": "Iara não é apenas uma sereia brasileira: sua lenda mistura uma guerreira indígena, o rio e um canto hipnótico"},
    {"id": "saci-pop", "titulo": "Saci-Pererê", "popular": 89, "angulo": "o Saci não nasceu com uma perna só: a versão mais conhecida mudou com o tempo"},
    {"id": "minotauro-pop", "titulo": "O Minotauro", "popular": 88, "angulo": "o Minotauro não nasceu em um labirinto: ele era filho de uma rainha e de um touro"},
    {"id": "fada-madrinha", "titulo": "A Fada Madrinha", "popular": 87, "angulo": "a fada madrinha dos contos antigos não era sempre bondosa e cobrava um preço pela ajuda"},

    # ---------------- Folclore e mitologia brasileira ----------------
    {"id": "curupira", "titulo": "O Curupira", "angulo": "o guardiao que imita vozes humanas para atrair caçadores ao erro"},
    {"id": "boitata", "titulo": "O Boitatá", "angulo": "a serpente de fogo que protege os campos de quem os queima"},
    {"id": "iara", "titulo": "A Iara", "angulo": "o canto do rio que faz homens desaparecerem para sempre"},
    {"id": "mapinguari", "titulo": "O Mapinguari", "angulo": "a criatura da floresta que exala um odor que apaga a memoria"},
    {"id": "saci", "titulo": "O Saci-Pererê", "angulo": "o redemoinho que rouba objetos e a sorte de quem o irrita"},
    {"id": "caipora", "titulo": "A Caipora", "angulo": "quem entra na mata sem pedir licença nunca mais caça nada"},
    {"id": "matinta", "titulo": "Matinta Pereira", "angulo": "o assobio noturno: quem responde recebe uma visita"},
    {"id": "pisadeira", "titulo": "A Pisadeira", "angulo": "o terror de dormir de barriga cheia"},
    {"id": "corpo-seco", "titulo": "O Corpo-Seco", "angulo": "o morto que a terra recusou e que se vinga dos vivos"},
    {"id": "mula", "titulo": "A Mula sem Cabeça", "angulo": "o castigo que galopa em chamas pela estrada"},
    {"id": "boto", "titulo": "O Boto Cor-de-Rosa", "angulo": "o sedutor que vira homem nas noites de festa"},
    {"id": "anhanga", "titulo": "Anhangá", "angulo": "o espirito protetor dos animais que persegue o caçador"},
    {"id": "cobra-grande", "titulo": "A Cobra Grande", "angulo": "a serpente adormecida sob os rios da Amazônia"},
    {"id": "vitoria-regia", "titulo": "A Vitória-Régia", "angulo": "a jovem que virou flor para seguir a lua"},
    {"id": "uirapuru", "titulo": "O Uirapuru", "angulo": "o canto que traz sorte a quem escuta e morte a quem procura"},
    {"id": "negrinho", "titulo": "O Negrinho do Pastoreio", "angulo": "a injustiça que virou milagre nas estradas do sul"},
    {"id": "cuca", "titulo": "A Cuca", "angulo": "a bruxa-jacaré que sequestra crianças desobedientes"},
    {"id": "lobisomem-br", "titulo": "O Lobisomem do Sertão", "angulo": "o sétimo filho, o cruzamento proibido e a maldição de sangue"},
    {"id": "tamandare", "titulo": "A Maldade de Tamandaré", "angulo": "o luto que criou a palmeira mais alta do Brasil"},
    {"id": "mae-ouro", "titulo": "A Mãe-de-Ouro", "angulo": "a aparição que protege o ouro escondido nas montanhas"},

    # ---------------- Grécia antiga ----------------
    {"id": "hades-persefone", "titulo": "Hades e Perséfone", "angulo": "a fruta que selou um casamento com o mundo dos mortos"},
    {"id": "cerbero", "titulo": "Cérbero", "angulo": "o cão de três cabeças que só dorme com música"},
    {"id": "caronte", "titulo": "Caronte", "angulo": "o barqueiro que cobrava a passagem e abandonava os insepultos"},
    {"id": "medusa", "titulo": "Medusa", "angulo": "a maldição que transforma o olhar em pedra"},
    {"id": "minotauro", "titulo": "O Minotauro", "angulo": "o labirinto construído para esconder um filho monstruoso"},
    {"id": "sisifo", "titulo": "O Castigo de Sísifo", "angulo": "a pedra que nunca chega ao topo"},
    {"id": "tantalo", "titulo": "O Suplício de Tântalo", "angulo": "fome e sede eternas a um palmo da água e do fruto"},
    {"id": "hecate", "titulo": "Hécate", "angulo": "a deusa dos cruzamentos, dos fantasmas e da magia proibida"},
    {"id": "nemesis", "titulo": "Nêmesis", "angulo": "a vingança que persegue quem tem sorte demais"},
    {"id": "prometeu", "titulo": "Prometeu", "angulo": "o fígado devorado todo dia por um ato de piedade"},
    {"id": "moiras", "titulo": "As Moiras", "angulo": "as três que cortam o fio da vida e nem Zeus contesta"},
    {"id": "tartaro", "titulo": "O Tártaro", "angulo": "a prisão mais profunda do universo, abaixo do próprio Hades"},
    {"id": "hidra", "titulo": "A Hidra de Lerna", "angulo": "a serpente que multiplica cada cabeça cortada"},
    {"id": "quimera", "titulo": "A Quimera", "angulo": "a criatura de três animais que respirava fogo"},
    {"id": "pandora", "titulo": "A Caixa de Pandora", "angulo": "o vaso que guardava todos os males do mundo"},
    {"id": "orfeu", "titulo": "Orfeu e Eurídice", "angulo": "a única regra que ele não conseguiu cumprir"},
    {"id": "asfodelos", "titulo": "Os Campos de Asfódelos", "angulo": "o lugar sem memória onde vagam os mortos comuns"},

    # ---------------- Nórdica ----------------
    {"id": "hel", "titulo": "Hel", "angulo": "a rainha de um reino feito de frio, fome e doença"},
    {"id": "fenrir", "titulo": "Fenrir", "angulo": "o lobo que os deuses criaram para ser acorrentado"},
    {"id": "jormungandr", "titulo": "Jörmungandr", "angulo": "a serpente que circula o mundo mordendo o próprio rabo"},
    {"id": "valquirias", "titulo": "As Valquírias", "angulo": "as escolhidas que decidem quem morre na batalha"},
    {"id": "niflheim", "titulo": "Niflheim", "angulo": "o mundo de gelo e névoa onde a vida começou"},
    {"id": "draugr", "titulo": "Os Draugr", "angulo": "os mortos que guardam seus próprios túmulos"},
    {"id": "yggdrasil", "titulo": "Yggdrasil", "angulo": "a árvore que sustenta nove mundos e apodrece por dentro"},

    # ---------------- Egito, Japão, Américas ----------------
    {"id": "anubis", "titulo": "Anúbis", "angulo": "a pesagem do coração contra a pena da verdade"},
    {"id": "ammit", "titulo": "Ammit", "angulo": "a devoradora dos corações condenados"},
    {"id": "osiris", "titulo": "Osíris", "angulo": "o deus despedaçado que virou rei dos mortos"},
    {"id": "kappa", "titulo": "O Kappa", "angulo": "o espírito do rio que rouba a força vital pelo umbigo"},
    {"id": "yurei", "titulo": "Os Yūrei", "angulo": "os mortos japoneses presos pela própria dor"},
    {"id": "jorogumo", "titulo": "Jorōgumo", "angulo": "a aranha que seduz homens antes de devorá-los"},
    {"id": "yomi", "titulo": "Yomi-no-Kuni", "angulo": "o país das trevas que contaminou uma deusa com podridão"},
    {"id": "mictlan", "titulo": "Mictlán", "angulo": "a travessia asteca de quatro anos pelo submundo"},
]


def next_topic(posted_ids):
    """Prioriza temas populares; depois percorre os demais sem repetir."""
    ordered = sorted(TOPICS, key=lambda t: (-t.get("popular", 0), TOPICS.index(t)))
    for t in ordered:
        if t["id"] not in posted_ids:
            return t
    return ordered[0]
