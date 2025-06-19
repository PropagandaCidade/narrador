// --- BANCO DE DADOS DE LOCUTORES ---
// Versão corrigida e organizada por gênero conforme a documentação oficial.

const voices = [
    // --- LOCUTORAS ---
    { id: 'aoede', name: 'Laura', gender: 'F', specialty: 'Ideal para narração e leitura de textos longos', imageUrl: 'assets/images/aoede.jpg', audioUrl: 'assets/audio/aoede.wav' },
    { id: 'autonoe', name: 'Beatriz', gender: 'F', specialty: 'Ótima para personagens e vozes de assistente', imageUrl: 'assets/images/autonoe.jpg', audioUrl: 'assets/audio/autonoe.wav' },
    { id: 'callirrhoe', name: 'Vanessa', gender: 'F', specialty: 'Excelente para vozes de personagens diversos', imageUrl: 'assets/images/callirrhoe.jpg', audioUrl: 'assets/audio/callirrhoe.wav' },
    { id: 'sulafat', name: 'Diana', gender: 'F', specialty: 'Voz de assistente, clara e conversacional', imageUrl: 'assets/images/sulafat.jpg', audioUrl: 'assets/audio/sulafat.wav' },
    { id: 'despina', name: 'Helena', gender: 'F', specialty: 'Perfeita para narração informativa e didática', imageUrl: 'assets/images/despina.jpg', audioUrl: 'assets/audio/despina.wav' },
    { id: 'vindemiatrix', name: 'Júlia', gender: 'F', specialty: 'Versátil para assistentes e personagens', imageUrl: 'assets/images/vindemiatrix.jpg', audioUrl: 'assets/audio/vindemiatrix.wav' },
    { id: 'achernar', name: 'Patrícia', gender: 'F', specialty: 'Boa para leitura de textos e narração', imageUrl: 'assets/images/achernar.jpg', audioUrl: 'assets/audio/achernar.wav' },
    { id: 'pulcherrima', name: 'Camila', gender: 'F', specialty: 'Ideal para voz de assistente e tutoriais', imageUrl: 'assets/images/pulcherrima.jpg', audioUrl: 'assets/audio/pulcherrima.wav' },
    { id: 'zephyr', name: 'Mariana', gender: 'F', specialty: 'Voz de personagem, energética e expressiva', imageUrl: 'assets/images/zephyr.jpg', audioUrl: 'assets/audio/zephyr.wav' },
    { id: 'kore', name: 'Amanda', gender: 'F', specialty: 'Excelente para narração de conteúdo', imageUrl: 'assets/images/kore.jpg', audioUrl: 'assets/audio/kore.wav' },

    // --- LOCUTORES ---
    { id: 'achird', name: 'Lucas', gender: 'M', specialty: 'Perfeito para narração e leitura', imageUrl: 'assets/images/achird.jpg', audioUrl: 'assets/audio/achird.wav' },
    { id: 'charon', name: 'André', gender: 'M', specialty: 'Voz de assistente, clara e objetiva', imageUrl: 'assets/images/charon.jpg', audioUrl: 'assets/audio/charon.wav' },
    { id: 'algenib', name: 'Fábio', gender: 'M', specialty: 'Ótimo para personagens e vozes criativas', imageUrl: 'assets/images/algenib.jpg', audioUrl: 'assets/audio/algenib.wav' },
    { id: 'alnilam', name: 'Bruno', gender: 'M', specialty: 'Excelente para vozes de personagens', imageUrl: 'assets/images/alnilam.jpg', audioUrl: 'assets/audio/alnilam.wav' },
    { id: 'algieba', name: 'Gustavo', gender: 'M', specialty: 'Ideal para narração de documentários', imageUrl: 'assets/images/algieba.jpg', audioUrl: 'assets/audio/algieba.wav' },
    { id: 'sadaltager', name: 'Rafael', gender: 'M', specialty: 'Voz de assistente, confiável e direta', imageUrl: 'assets/images/sadaltager.jpg', audioUrl: 'assets/audio/sadaltager.wav' },
    { id: 'zubenelgenubi', name: 'Sérgio', gender: 'M', specialty: 'Voz de personagem, versátil e adaptável', imageUrl: 'assets/images/zubenelgenubi.jpg', audioUrl: 'assets/audio/zubenelgenubi.wav' },
    { id: 'umbriel', name: 'Thiago', gender: 'M', specialty: 'Perfeito para assistentes virtuais', imageUrl: 'assets/images/umbriel.jpg', audioUrl: 'assets/audio/umbriel.wav' },
    { id: 'fenrir', name: 'Eduardo', gender: 'M', specialty: 'Bom para narração de textos e e-learning', imageUrl: 'assets/images/fenrir.jpg', audioUrl: 'assets/audio/fenrir.wav' },
    { id: 'sadachbia', name: 'Leandro', gender: 'M', specialty: 'Ótimo para leitura e narração de conteúdo', imageUrl: 'assets/images/sadachbia.jpg', audioUrl: 'assets/audio/sadachbia.wav' },
    { id: 'iapetus', name: 'Ricardo', gender: 'M', specialty: 'Voz de assistente e conversacional', imageUrl: 'assets/images/iapetus.jpg', audioUrl: 'assets/audio/iapetus.wav' },
    { id: 'enceladus', name: 'Vitor', gender: 'M', specialty: 'Ideal para vozes de personagens e jogos', imageUrl: 'assets/images/enceladus.jpg', audioUrl: 'assets/audio/enceladus.wav' },
    { id: 'schedar', name: 'Rodrigo', gender: 'M', specialty: 'Voz de narração, clara e profissional', imageUrl: 'assets/images/schedar.jpg', audioUrl: 'assets/audio/schedar.wav' },
    { id: 'rasalgethi', name: 'Felipe', gender: 'M', specialty: 'Excelente para assistente e aplicações', imageUrl: 'assets/images/rasalgethi.jpg', audioUrl: 'assets/audio/rasalgethi.wav' },
    { id: 'orus', name: 'Fernando', gender: 'M', specialty: 'Ótimo para narração de documentários e vídeos', imageUrl: 'assets/images/orus.jpg', audioUrl: 'assets/audio/orus.wav' },
    { id: 'puck', name: 'Paulo', gender: 'M', specialty: 'Voz de personagem, expressiva e criativa', imageUrl: 'assets/images/puck.jpg', audioUrl: 'assets/audio/puck.wav' }
    
];