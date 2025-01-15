        features: Dict[str, Any],
        result: Dict[str, Any]) -> float:
        """Calculate potential impact of innovation"""
        impact_scores = []
        
        # Performance impact
        if 'performance_improvement' in features:
            impact_scores.append(features['performance_improvement'])
        
        # Resource efficiency impact
        if 'resource_efficiency' in features:
            impact_scores.append(features['resource_efficiency'])
        
        # Quality impact
        if 'quality_improvement' in features:
            impact_scores.append(features['quality_improvement'])
        
        return np.mean(impact_scores) if impact_scores else 0.0

    def _determine_innovation_type(self, features: Dict[str, Any]) -> str:
        """Determine type of innovation"""
        if 'performance_improvement' in features and features['performance_improvement'] > 0.8:
            return 'performance_breakthrough'
        elif 'resource_efficiency' in features and features['resource_efficiency'] > 0.8:
            return 'efficiency_breakthrough'
        elif 'quality_improvement' in features and features['quality_improvement'] > 0.8:
            return 'quality_breakthrough'
        else:
            return 'incremental_improvement'

    async def _execute_lm_studio(self,
                               model: str,
                               task: Dict[str, Any],
                               adaptations: Dict[str, Any]) -> Any:
        """Execute task using LM Studio model"""
        try:
            # Prepare request
            endpoint = "http://localhost:1234/v1/chat/completions"
            
            # Apply adaptations
            temperature = 0.1 if adaptations.get('optimize_speed') else 0.7
            max_tokens = 2048 if adaptations.get('reduce_memory') else 4096
            
            # Prepare prompt with task requirements
            messages = [
                {"role": "system", "content": "You are a precise and efficient problem-solving assistant."},
                {"role": "user", "content": json.dumps(task)}
            ]
            
            # Make request
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    endpoint,
                    json={
                        "model": model.split('.')[1],
                        "messages": messages,
                        "temperature": temperature,
                        "max_tokens": max_tokens
                    }
                ) as response:
                    result = await response.json()
                    
                    if 'choices' in result:
                        return result['choices'][0]['message']['content']
                    else:
                        raise Exception(f"Invalid response: {result}")
                        
        except Exception as e:
            self.logger.error(f"LM Studio execution failed: {e}")
            raise

    async def _execute_ollama(self,
                            model: str,
                            task: Dict[str, Any],
                            adaptations: Dict[str, Any]) -> Any:
        """Execute task using Ollama model"""
        try:
            # Prepare request
            endpoint = "http://localhost:11434/api/generate"
            
            # Apply adaptations
            temperature = 0.1 if adaptations.get('optimize_speed') else 0.7
            num_predict = 2048 if adaptations.get('reduce_memory') else 4096
            
            # Make request
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    endpoint,
                    json={
                        "model": model.split('.')[1],
                        "prompt": json.dumps(task),
                        "temperature": temperature,
                        "num_predict": num_predict
                    }
                ) as response:
                    result = await response.json()
                    
                    if 'response' in result:
                        return result['response']
                    else:
                        raise Exception(f"Invalid response: {result}")
                        
        except Exception as e:
            self.logger.error(f"Ollama execution failed: {e}")
            raise

    async def _execute_jan(self,
                        model: str,
                        task: Dict[str, Any],
                        adaptations: Dict[str, Any]) -> Any:
        """Execute task using Jan inference"""
        try:
            # Prepare request
            endpoint = "http://localhost:39291/v1/completions"
            
            # Apply adaptations
            temperature = 0.1 if adaptations.get('optimize_speed') else 0.7
            max_tokens = 2048 if adaptations.get('reduce_memory') else 4096
            
            # Make request
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    endpoint,
                    json={
                        "model": model.split('.')[1],
                        "prompt": json.dumps(task),
                        "temperature": temperature,
                        "max_tokens": max_tokens
                    }
                ) as response:
                    result = await response.json()
                    
                    if 'choices' in result:
                        return result['choices'][0]['text']
                    else:
                        raise Exception(f"Invalid response: {result}")
                        
        except Exception as e:
            self.logger.error(f"Jan execution failed: {e}")
            raise

    async def get_engine_stats(self) -> Dict[str, Any]:
        """Get comprehensive engine statistics"""
        return {
            'active_battles': len(self.active_battles),
            'patterns_detected': len(self.pattern_memory),
            'innovations_detected': len(self.innovation_memory),
            'executions_completed': len(self.execution_history),
            'model_adaptations': {
                model: list(adaptations.keys())
                for model, adaptations in self.model_adaptations.items()
            },
            'competition_metrics': {
                model: {
                    metric: np.mean(values)
                    for metric, values in metrics.items()
                }
                for model, metrics in self.competition_metrics.items()
            }
        }

    async def cleanup(self):
        """Cleanup engine resources"""
        try:
            # Clear memory
            self.pattern_memory.clear()
            self.innovation_memory.clear()
            self.execution_history.clear()
            
            # Clear metrics and adaptations
            self.competition_metrics.clear()
            self.model_adaptations.clear()
            
            # Clear active battles
            self.active_battles.clear()
            
            self.logger.info("Battle engine cleanup completed")
        except Exception as e:
            self.logger.error(f"Battle engine cleanup failed: {e}")
            raise
