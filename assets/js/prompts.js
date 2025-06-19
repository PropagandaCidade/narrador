// --- BANCO DE DADOS DE OPÇÕES E PROMPTS ---

// Opções que aparecerão nos menus <select> de Formato
const formatOptions = [
    { value: 'spot_comercial', text: 'Spot Comercial' },
    { value: 'carro_de_som', text: 'Carro de Som' },
    { value: 'carro_de_vendas', text: 'Carro de Vendas' },
    { value: 'vinhetas', text: 'Vinhetas' },
    { value: 'audiovisual', text: 'Audiovisual' },
    { value: 'chamada_de_festa', text: 'Chamada de Festa' },
    { value: 'vsl', text: 'VSL (Vídeo de Vendas)' },
    { value: 'vt_comercial', text: 'VT Comercial' },
    { value: 'aberturas', text: 'Aberturas' },
    { value: 'espera_telefonica', text: 'Espera Telefônica' },
    { value: 'gravacao_politica', text: 'Gravação Política' },
    { value: 'post_em_audio', text: 'Post em Áudio' }
];

// Opções que aparecerão nos menus <select> de Estilo
const styleOptions = [
    { value: 'padrao', text: 'Padrão' },
    { value: 'impacto', text: 'Impacto' },
    { value: 'animada', text: 'Animada' },
    { value: 'varejo', text: 'Varejo' },
    { value: 'caricata', text: 'Caricata' }
];

// Mapeamento completo dos prompts em inglês por Formato e Estilo
const prompts = {
    spot_comercial: {
        padrao: "A clear, friendly, and professional voice for a standard commercial advertisement:",
        impacto: "A powerful, emphatic, and engaging voice for a high-impact commercial spot:",
        animada: "A lively and upbeat announcer voice delivering an enthusiastic commercial spot:",
        varejo: "An energetic and persuasive retail commercial voice, highlighting big sales and deals:",
        caricata: "A comically animated voice for a humorous or parody-style commercial:"
    },
    carro_de_som: {
        padrao: "A clear and steady voice for a traditional moving car loudspeaker ad:",
        impacto: "A bold and forceful voice for a street car ad, capturing immediate attention with intensity:",
        animada: "An energetic and cheerful voice for a festive loudspeaker car ad:",
        varejo: "A loud and enthusiastic voice for a street loudspeaker ad, energetic and direct:",
        caricata: "A comically exaggerated street announcement voice, playful and over-the-top, as if from a loudspeaker truck:"
    },
    carro_de_vendas: {
        padrao: "A neutral, informative tone promoting products clearly from a moving vehicle:",
        impacto: "A commanding and persuasive voice promoting products from a moving sales vehicle:",
        animada: "A lively and enthusiastic street vendor voice promoting products from a moving vehicle:",
        varejo: "A direct and upbeat loudspeaker sales voice from a moving vehicle, with an urgent and persuasive tone:",
        caricata: "A humorous, over-the-top sales voice with comical expressions from a vendor car:"
    },
    vinhetas: {
        padrao: "A simple, clean voice setting up the jingle without exaggeration:",
        impacto: "A bold and commanding voice setting a strong tone at the beginning of a jingle:",
        animada: "A bright, upbeat, and cheerful voice for a catchy jingle intro:",
        varejo: "A catchy and enthusiastic voice highlighting product deals in a musical intro:",
        caricata: "A cartoonish, exaggerated, and playful voice for a comedic audio jingle:"
    },
    audiovisual: {
        padrao: "A clear and professional narrator voice for an informative audiovisual presentation:",
        impacto: "A dramatic and cinematic narrator voice for a high-impact trailer or video segment:",
        animada: "An energetic narrator guiding viewers with enthusiasm and charm:",
        varejo: "A sales-focused voice guiding through audiovisual content with commercial flair:",
        caricata: "A cartoonish, exaggerated voice suited for playful animations or humorous AV content:"
    },
    chamada_de_festa: {
        padrao: "An announcer voice hyping up a party event:",
        impacto: "A strong, party-hype voice inviting everyone with high energy and force:",
        animada: "An excited and upbeat announcer voice hyping up a party event, with a festive tone:",
        varejo: "A festive sales tone, mixing fun and promotions for an event:",
        caricata: "A playful, animated voiceover hyping a party in a fun and exaggerated tone:"
    },
    vsl: {
        padrao: "A clear and conversational narrator voice for a persuasive video sales letter, with a friendly and confident tone:",
        impacto: "A dynamic, emotionally driven voice for a persuasive and dramatic VSL:",
        animada: "An enthusiastic and engaging narrator for an energetic video sales letter:",
        varejo: "A commercial-style voice focused on urgency, savings, and benefits in a VSL:",
        caricata: "An exaggerated and fun delivery to make the sales pitch humorous and memorable:"
    },
    vt_comercial: {
        padrao: "A professional and polished voice for a clean, corporate video commercial:",
        impacto: "A dramatic and convincing tone to highlight products in a powerful way:",
        animada: "A dynamic and upbeat delivery to energize the viewer in a video ad:",
        varejo: "A sales-driven, promotional tone pushing discounts and deals visually:",
        caricata: "An entertaining and cartoon-like voice for a humorous TV-style ad:"
    },
    aberturas: {
        padrao: "A confident and polished voice for the opening of a professional segment or podcast:",
        impacto: "A powerful and dramatic voiceover for an impactful show opener:",
        animada: "A fun and upbeat announcer voice opening a show with enthusiasm and energy:",
        varejo: "An energetic and promotional voice introducing a retail program or show:",
        caricata: "A theatrical, whimsical voice opening a humorous or animated segment:"
    },
    espera_telefonica: {
        padrao: "A calm, friendly, and reassuring voice for a telephone on-hold message:",
        impacto: "A relaxed, explanatory tone as if guiding a client patiently on hold:",
        animada: "A cheerful and friendly voice for telephone hold lines, keeping the caller engaged:",
        varejo: "A persuasive voice promoting store offers and services while the caller waits:",
        caricata: "A whimsical and entertaining voice for humorous on-hold messages:"
    },
    gravacao_politica: {
        padrao: "A serious, articulate, and composed voice for formal political campaign messaging:",
        impacto: "An authoritative and impassioned voice delivering a political campaign message with conviction:",
        animada: "An inspired and hopeful voice calling voters to action in a vibrant tone:",
        varejo: "A persuasive and urgent voice presenting political promises in a retail-like tone:",
        caricata: "A humorous and exaggerated delivery for a satirical political voiceover:"
    },
    post_em_audio: {
        padrao: "A clean and professional voice narrating an informative or personal audio post:",
        impacto: "A dramatic, striking voice for an attention-grabbing audio post or ad:",
        animada: "A casual, fun, and friendly voice for relaxed and engaging audio content:",
        varejo: "A fast-paced, urgent voice emphasizing deals in a short audio post format:",
        caricata: "A silly and over-the-top voice for a comedic audio post, with playful and exaggerated intonation:"
    }
};

// --- NOVAS CONSTANTES PARA VELOCIDADE ---

// Opções para o menu de Velocidade
const speedOptions = [
    { value: '1', text: '1. Lento' },
    { value: '2', text: '2. Normal' },
    { value: '3', text: '3. Rápido' },
    { value: '4', text: '4. Super Rápido' },
    { value: '5', text: '5. Mega Rápido' }
];

// Mapeamento dos valores de velocidade para os prompts em inglês
const speedPrompts = {
    '1': "Read at a slow and deliberate pace.",
    '2': "", // Deixamos vazio, pois "normal" não precisa de instrução extra
    '3': "Read at a fast pace.",
    '4': "Read at a very fast pace.",
    '5': "Read at an extremely fast pace, as fast as possible while maintaining clarity."
};