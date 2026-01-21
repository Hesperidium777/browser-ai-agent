import json
from typing import Dict, Any, List, Optional
from datetime import datetime
import hashlib
from dataclasses import dataclass, asdict

@dataclass
class Episode:
    """Эпизод памяти"""
    id: str
    url: str
    title: str
    page_type: str
    actions: List[Dict[str, Any]]
    timestamp: str
    success: bool
    learned_patterns: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class EpisodicMemory:
    """Эпизодическая память для агента"""
    
    def __init__(self, storage_file: str = "episodic_memory.json"):
        self.storage_file = storage_file
        self.episodes: List[Episode] = []
        self.patterns: Dict[str, int] = {}  # Паттерн -> количество использований
        
        self.load()
    
    def add_episode(self, 
                   url: str, 
                   title: str, 
                   page_type: str,
                   actions: List[Dict[str, Any]],
                   success: bool) -> Episode:
        """Добавление нового эпизода"""
        episode_id = self._generate_id(url, title, actions)
        
        # Извлекаем паттерны из действий
        learned_patterns = self._extract_patterns(actions)
        
        episode = Episode(
            id=episode_id,
            url=url,
            title=title,
            page_type=page_type,
            actions=actions,
            timestamp=datetime.now().isoformat(),
            success=success,
            learned_patterns=learned_patterns
        )
        
        self.episodes.append(episode)
        
        # Обновляем частоту паттернов
        for pattern in learned_patterns:
            self.patterns[pattern] = self.patterns.get(pattern, 0) + 1
        
        self.save()
        return episode
    
    def find_similar_episodes(self, 
                            url: Optional[str] = None,
                            page_type: Optional[str] = None,
                            max_results: int = 5) -> List[Episode]:
        """Поиск похожих эпизодов"""
        scored_episodes = []
        
        for episode in self.episodes:
            score = 0
            
            if url and url in episode.url:
                score += 2
            
            if page_type and episode.page_type == page_type:
                score += 1
            
            if episode.success:
                score += 1
            
            if score > 0:
                scored_episodes.append((score, episode))
        
        # Сортируем по убыванию score
        scored_episodes.sort(key=lambda x: x[0], reverse=True)
        
        return [ep for _, ep in scored_episodes[:max_results]]
    
    def get_patterns_for_page_type(self, page_type: str) -> List[str]:
        """Получение паттернов для типа страницы"""
        relevant_patterns = []
        
        for episode in self.episodes:
            if episode.page_type == page_type and episode.success:
                relevant_patterns.extend(episode.learned_patterns)
        
        # Сортируем по частоте
        pattern_freq = {}
        for pattern in relevant_patterns:
            pattern_freq[pattern] = pattern_freq.get(pattern, 0) + 1
        
        sorted_patterns = sorted(pattern_freq.items(), key=lambda x: x[1], reverse=True)
        return [pattern for pattern, _ in sorted_patterns[:10]]
    
    def _generate_id(self, url: str, title: str, actions: List[Dict[str, Any]]) -> str:
        """Генерация ID эпизода"""
        content = f"{url}_{title}_{len(actions)}"
        return hashlib.md5(content.encode()).hexdigest()[:8]
    
    def _extract_patterns(self, actions: List[Dict[str, Any]]) -> List[str]:
        """Извлечение паттернов из действий"""
        patterns = []
        
        for i in range(len(actions) - 1):
            action1 = actions[i]
            action2 = actions[i + 1]
            
            # Паттерны последовательностей действий
            pattern = f"{action1.get('action_type')} -> {action2.get('action_type')}"
            patterns.append(pattern)
            
            # Паттерны для определенных типов страниц
            if "login" in action1.get('action_description', '').lower():
                patterns.append("login_sequence")
            if "search" in action1.get('action_description', '').lower():
                patterns.append("search_sequence")
            if "click" in action1.get('action_type', '') and "type" in action2.get('action_type', ''):
                patterns.append("click_then_type")
        
        return list(set(patterns))
    
    def get_advice(self, current_state: Dict[str, Any]) -> str:
        """Получение советов на основе прошлого опыта"""
        page_type = current_state.get('page_type', 'general')
        similar_episodes = self.find_similar_episodes(page_type=page_type)
        
        if not similar_episodes:
            return ""
        
        advice_parts = ["=== СОВЕТЫ ИЗ ПРОШЛОГО ОПЫТА ==="]
        
        for i, episode in enumerate(similar_episodes[:3], 1):
            advice_parts.append(f"\nПример {i} ({'успешно' if episode.success else 'неудачно'}):")
            advice_parts.append(f"Страница: {episode.title}")
            
            # Показываем ключевые действия
            key_actions = []
            for action in episode.actions[-5:]:  # Последние 5 действий
                if action.get('result', {}).get('success'):
                    key_actions.append(f"- {action.get('action_description', '')}")
            
            if key_actions:
                advice_parts.append("Действия:")
                advice_parts.extend(key_actions)
            
            # Показываем извлеченные паттерны
            if episode.learned_patterns:
                advice_parts.append(f"Паттерны: {', '.join(episode.learned_patterns[:3])}")
        
        return "\n".join(advice_parts)
    
    def save(self):
        """Сохранение памяти в файл"""
        data = {
            "episodes": [episode.to_dict() for episode in self.episodes],
            "patterns": self.patterns
        }
        
        try:
            with open(self.storage_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Ошибка при сохранении памяти: {e}")
    
    def load(self):
        """Загрузка памяти из файла"""
        try:
            with open(self.storage_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.episodes = [Episode(**ep) for ep in data.get("episodes", [])]
            self.patterns = data.get("patterns", {})
        except FileNotFoundError:
            # Файл не существует, начнем с пустой памяти
            self.episodes = []
            self.patterns = {}
        except Exception as e:
            print(f"Ошибка при загрузке памяти: {e}")